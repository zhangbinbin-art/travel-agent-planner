"""多步 Agent 运行器（v1.2 增量优化版）。

能力：
- ReAct 循环：模型 → 工具 → 观察 → 再决策，最多 MAX_STEPS 步；
- 偏好快照隔离：每轮使用「本轮面板偏好快照」，与对话历史分开存储；
- 需求冲突预检测：调用工具前先跑规则表，冲突则让模型先向用户确认；
- 单工具局部降级 + 单工具超时：某个工具失败/超时不影响其它工具结果；
- 结构化日志：每次自检、每次重排都带 trace_id 落日志，便于复现；
- 无 Key / 模型不可用时整体降级为「关键词解析 + 确定性路线」。
"""
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from services import ai_agent, agent_tools

MAX_STEPS = 8
# 单次会话保留的消息条数（含 tool 消息）
MAX_HISTORY = 20
# 单条 tool 结果回填的字符上限
TOOL_RESULT_LIMIT = 4000
# 单个工具超时（秒）：超时只标记该工具失败，不整体降级
TOOL_TIMEOUT = 12

AGENT_SYSTEM_PROMPT = (
    "你是国内旅行规划 Agent。你可以调用工具查询景点、生成路线、自检路线、查询酒店。"
    "规则："
    "1) 涉及具体城市时，先用 search_spots 查看真实景点，再调用 make_route；"
    "2) 用户提到预算或住宿时，用 search_hotels；"
    "3) 偏好只能使用：自然风光、人文古迹、美食探店、游乐乐园、城市逛街、徒步登山、海滨海岛、亲子出游；"
    "4) 工具返回的景点/价格必须原样引用，不得编造；"
    "5) 回答只围绕景点与行程本身：景点信息、票价、口碑评论、适合人群、路线安排；"
    "不要输出系统实现细节（算法限制、参数快照、工具名、自检分数、trace 等），"
    "禁止出现「当前算法不支持…」「需要先说明一个限制」这类解释，直接给最接近的可执行方案；"
    "6) 与旅行无关的请求直接拒绝；"
    "7) 不要重复调用同一工具和同一组参数；"
    "8) 只能引用工具返回的字段（景点名、票价、距离、酒店名、房价、距离公里数）；"
    "工具没返回的评分、里程、票价一律不许补写，也不要估算；"
    "9) 需要具体数据时必须先调用工具；没有工具结果时只能说不确定，不得编造；"
    "10) 历史工具事实由系统提供，以此为准；禁止否认已发生的工具调用，也不得声称自己“编造了数据”；"
    "11) 用户要求逐日主题（如第一天爬山、第二天逛历史）时，直接用整体偏好尽量贴近，"
    "不要解释算法限制、不要反问确认；"
    "12) 用户要求「酒店离景点近 / N 公里内」但没给圆心时：有路线就用路线第一个景点，"
    "没有先 make_route 再取首站；调用 search_hotels 传 near_spot + radius_km（默认 5），回复写明圆心与半径；"
    "13) 每次 make_route 之后必须调用 critique_route 自检（传景点名、主/次偏好、天数、每日数量；"
    "涉及酒店时传 hotel_list / hotel_budget / hotel_tags / hotel_max_radius）；"
    "若 issues 中 level=severe 或存在可修复的 warn，最多重排一次 make_route；"
    "重排必须真正改变参数：把自检 issues 里所有 code=spot_pref / spot_missing 的 target "
    "一次性放进 exclude_spots 再排，禁止用完全相同的参数重排；重排后如实报告前后差异；"
    "14) 自检返回的 issues_text 是给用户看的原话，转述时保持通俗；"
    "distance_note 必须保留「球面距离≠路网通勤耗时」的说明；"
    "15) 若系统提示检测到需求冲突，先向用户确认是否调整，确认前不要再调用工具；"
    "16) 描述每天的属性必须有数据依据：某天内命中该主偏好的景点不足一半时，"
    "只能说「以…为主」并写明命中数量，不得说「第一天就是爬山日 / 第二天就是逛街日」；"
    "17) 不要用「完全符合」这类绝对化表述，如有未命中偏好的景点必须点名说明；"
    "18) 偏好只能来自用户明确表达：用户没提的偏好不得自行加入 preferences / main / secondary，"
    "否则自检会把「自行添加的偏好」当成合规依据，掩盖真实缺口；"
    "22) 若用户点名某类偏好（如游乐园）但路线未覆盖，必须先调用 search_spots 核实该类资源是否存在；"
    "存在就说明「因距离/名额限制未排入」，不存在才说没有；禁止凭印象声称库里没有；"
    "21) 用户追加需求（如「第三天想去游乐园」「再加一天」「换成三天」）时，"
    "直接理解为调整天数/补充偏好并立即调用 make_route 重排，不要反问确认；"
    "只有缺少目标城市时才询问；重排后在回复里说明新的天数与景点，不要提参数或算法细节；"
    "20) 用户询问景点特色、适合人群（带娃/老人/情侣）、口碑评价、室内或雨天推荐等非结构化问题时，"
    "必须先调用 search_knowledge；回答要转述具体内容并注明来源景点，不得编造；"
    "检索为空要明确说「知识库未收录」，不要用常识补；不要把片段整段复制，控制在 150 字内。"
    "19) 若 make_route 返回的 day_plans 数量少于用户要求的天数（说明后面几天没排到景点），"
    "不要直接交付：先降低 per_day 再排一次（例如 3 天原本 per_day=3，可改为 2），"
    "目标是让每天都有景点；若降低到 1 仍排不满，才如实说明「第X天没有可排景点，页面只显示前几天」并给出建议。"
)

# 进程内会话记忆：session_id -> messages（不含 system）
_SESSIONS: Dict[str, List[dict]] = {}
# 会话工具事实：session_id -> [事实摘要]
_FACTS: Dict[str, List[str]] = {}
# 偏好快照：session_id -> {preferences, main_preferences, secondary_preferences, days, per_day, travel_type, budget}
_SNAPSHOTS: Dict[str, dict] = {}
FACT_TURNS = 6
FACT_MAX_CHARS = 1800
FACT_ITEM_CHARS = 400

# ---------------------------------------------------------------------------
# 需求冲突预检测（规则表，可扩展）
# ---------------------------------------------------------------------------
# 每条规则：code + 判定函数 + 给 LLM 的中文提示
CONFLICT_RULES = [
    {
        "code": "family_hiking",
        "match": lambda c: c["travel_type"] in ("家庭亲子", "老年休闲") and "徒步登山" in c["preferences"],
        "message": "出行人群是「{travel_type}」却选了高强度「徒步登山」，可能体力吃不消；是否改成自然风光或减少爬山安排？",
    },
    {
        "code": "elder_hiking",
        "match": lambda c: c["travel_type"] == "老年休闲" and "徒步登山" in c["preferences"],
        "message": "老年休闲通常不适合长时间登山，是否换成长时间步行较少的景点？",
    },
    {
        "code": "low_budget_park",
        "match": lambda c: c["low_budget"] and (
            "游乐乐园" in c["preferences"] or any(k in c["text"] for k in ("乐园", "长隆", "游乐园"))),
        "message": "预算偏低但选择了游乐乐园（热门乐园门票通常较高），是否放宽预算或替换为免费公园？",
    },
    {
        "code": "short_trip_far",
        "match": lambda c: c["days"] == 1 and c["per_day"] >= 4,
        "message": "只有 1 天却安排 4 个以上景点，通勤时间可能不够；是否减少景点数量或增加天数？",
    },
]

LOW_BUDGET_KEYWORDS = ("预算低", "预算有限", "穷游", "省钱", "便宜", "学生党", "人均低")


def _detect_conflicts(text: str, snapshot: dict) -> List[dict]:
    """在调用工具前检测「人群/偏好/预算/天数」的冲突组合。"""
    ctx = {
        "text": text or "",
        "preferences": list(snapshot.get("preferences") or []),
        "travel_type": snapshot.get("travel_type") or "单人出行",
        "days": int(snapshot.get("days") or 0) or 0,
        "per_day": int(snapshot.get("per_day") or 0) or 0,
        "low_budget": any(k in (text or "") for k in LOW_BUDGET_KEYWORDS)
        or (snapshot.get("hotel_budget") is not None and float(snapshot.get("hotel_budget") or 0) <= 150),
    }
    conflicts = []
    for rule in CONFLICT_RULES:
        try:
            if rule["match"](ctx):
                conflicts.append({
                    "code": rule["code"],
                    "message": rule["message"].format(**ctx),
                })
        except Exception:
            continue
    return conflicts


# ---------------------------------------------------------------------------
# 记忆 / 事实 / 快照
# ---------------------------------------------------------------------------

def _facts_text(session_id: str) -> str:
    facts = _FACTS.get(session_id) or []
    if not facts:
        return ""
    text = "\n".join(facts)
    return text[-FACT_MAX_CHARS:]


def _remember_facts(session_id: str, facts: List[str]) -> None:
    """事实单独压缩存储：单条截断 + 只保留最近 FACT_TURNS 条。"""
    if not facts:
        return
    trimmed = [(f[:FACT_ITEM_CHARS]) for f in facts if f]
    merged = (_FACTS.get(session_id) or []) + trimmed
    _FACTS[session_id] = merged[-FACT_TURNS:]


def _snapshot_text(snapshot: dict) -> str:
    if not snapshot:
        return ""
    parts = []
    if snapshot.get("preferences"):
        parts.append("偏好=%s" % "/".join(snapshot["preferences"]))
    if snapshot.get("main_preferences"):
        parts.append("主偏好=%s" % "/".join(snapshot["main_preferences"]))
    if snapshot.get("secondary_preferences"):
        parts.append("次偏好=%s" % "/".join(snapshot["secondary_preferences"]))
    if snapshot.get("travel_type"):
        parts.append("人群=%s" % snapshot["travel_type"])
    if snapshot.get("days"):
        parts.append("天数=%s" % snapshot["days"])
    if snapshot.get("per_day"):
        parts.append("每日=%s" % snapshot["per_day"])
    if snapshot.get("hotel_budget") is not None:
        parts.append("酒店预算=%s" % snapshot["hotel_budget"])
    if snapshot.get("origin"):
        parts.append("来源=%s" % snapshot["origin"])
    return "；".join(parts)


def _update_snapshot(sid: str, args: dict) -> dict:
    """用本轮工具参数更新偏好快照；旧轮次偏好不会污染本轮。"""
    current = dict(_SNAPSHOTS.get(sid) or {})
    for key in ("target_city", "preferences", "days", "per_day", "travel_type",
                "start_location", "hotel_budget"):
        if args.get(key) is not None:
            current[key] = args[key]
    current["origin"] = "tool_args"
    _SNAPSHOTS[sid] = current
    return current


def _fact_from_tool(name: str, args: dict, result: dict, trace_id: Optional[str] = None) -> str:
    """把工具结果压成一句可复用的事实，只保留模型允许引用的字段。"""
    if "error" in result:
        return "工具 %s 参数=%s 执行失败：%s" % (
            name, json.dumps(args, ensure_ascii=False)[:200], result["error"]
        )
    if name == "search_spots":
        names = "、".join(
            "%s(%s元)" % (x.get("name"), x.get("price")) for x in (result.get("spots") or [])[:10]
        )
        return "查询景点 city=%s：共 %s 条，匹配 %s 条，返回：%s" % (
            result.get("city"), result.get("total"), result.get("matched"), names or "无"
        )
    if name == "make_route":
        route = " → ".join(
            "%s(%s元)" % (x.get("name"), x.get("price")) for x in (result.get("route_list") or [])
        )
        days = "；".join(
            "第%s天:%s" % (d.get("day"), "、".join(d.get("spots") or []))
            for d in (result.get("day_plans") or [])
        )
        return "生成路线 days=%s：%s；分组：%s；总里程=%s km；tips=%s" % (
            args.get("days"), route or "无", days or "无", result.get("total_distance"), result.get("tips")
        )
    if name == "critique_route":
        texts = result.get("issues_text") or []
        return "自检结果 score=%s ok=%s 得分明细=%s；问题=%s" % (
            result.get("score"), result.get("ok"),
            json.dumps(result.get("score_breakdown"), ensure_ascii=False),
            "；".join(texts) or "无",
        )
    if name == "search_knowledge":
        hits = "、".join(
            "%s(%.2f)" % (h.get("spot"), h.get("score") or 0) for h in (result.get("hits") or [])[:4]
        )
        return "知识库检索 query=%s：命中 %s 条：%s；note=%s" % (
            result.get("query"), result.get("count"), hits or "无", result.get("note") or "无"
        )
    if name == "search_hotels":
        hotels = "、".join(
            "%s(%s元%s)" % (
                h.get("name"), h.get("price_per_day"),
                "" if h.get("distance_km") is None else ",%skm" % h.get("distance_km"),
            )
            for h in (result.get("hotels") or [])[:8]
        )
        return "查询酒店 city=%s near=%s radius=%s：返回 %s 条：%s" % (
            result.get("city"), result.get("near_spot"), result.get("radius_km"),
            result.get("count"), hotels or "无"
        )
    return "工具 %s 返回：%s" % (name, json.dumps(result, ensure_ascii=False)[:300])


# ---------------------------------------------------------------------------
# 模型调用 / 工具执行
# ---------------------------------------------------------------------------

def _norm_route_args(args: dict) -> dict:
    """把 make_route 参数归一化成可比较的字典，用于判断是否为无效重排。"""
    prefs = args.get("preferences") or []
    return {
        "target_city": (args.get("target_city") or "").strip(),
        "days": int(args.get("days") or 0),
        "per_day": int(args.get("per_day") or 0),
        "preferences": sorted(str(p) for p in prefs),
        "travel_type": args.get("travel_type") or "",
        "start_location": (args.get("start_location") or "").strip(),
        "exclude_spots": sorted(str(n) for n in (args.get("exclude_spots") or [])),
    }


def _chat(messages: List[dict], tools: Optional[List[dict]] = None) -> dict:
    """调用 DeepSeek chat/completions；失败抛异常由上层决定降级。"""
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "thinking": {"type": "disabled"},
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    url = settings.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": "Bearer %s" % settings.DEEPSEEK_API_KEY,
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=settings.DEEPSEEK_TIMEOUT) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def _execute_with_timeout(name: str, args: dict, db: Session,
                          trace_id: str) -> dict:
    """单工具超时控制：超时只让该工具失败，不影响其它工具。"""
    started = time.time()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(agent_tools.execute_tool, name, args, db, trace_id)
        try:
            result = future.result(timeout=TOOL_TIMEOUT)
        except FutureTimeout:
            agent_tools._log("tool_timeout", trace_id, tool=name, args=args, timeout=TOOL_TIMEOUT)
            return {"error": "工具 %s 超时（>%ss）" % (name, TOOL_TIMEOUT), "degraded": True}
        except Exception as exc:
            agent_tools._log("tool_error", trace_id, tool=name, error=str(exc))
            return {"error": "工具 %s 异常：%s" % (name, exc), "degraded": True}
    agent_tools._log(
        "tool_done", trace_id, tool=name, args=args,
        elapsed=round(time.time() - started, 2),
        degraded=bool(result.get("degraded")),
    )
    return result


def _degraded_run(db: Session, message: str, history: List[dict]) -> dict:
    """无 Key / 模型不可用：复用关键词解析 + 确定性算法，保证功能可演示。"""
    parsed = ai_agent.plan_from_message(db, message)
    params = parsed.get("params") or {}
    route = None
    tips = parsed.get("reply") or ""
    if params.get("target_city"):
        try:
            route = agent_tools.tool_make_route(
                db,
                target_city=params["target_city"],
                days=params.get("days") or 2,
                per_day=params.get("per_day") or 3,
                preferences=params.get("preferences") or [],
                travel_type=params.get("travel_type") or "单人出行",
                start_location=params.get("start_location"),
            )
            names = "、".join(x["name"] for x in route.get("route_list") or [])
            reply = "%s。已生成路线：%s。" % (tips, names or "无可用景点")
            if route.get("tips"):
                reply += route["tips"]
        except Exception as exc:
            reply = "%s。路线生成失败：%s" % (tips, exc)
    else:
        reply = tips or "未能识别目的地，请补充城市后重试"

    return {
        "reply": reply,
        "route": route,
        "params": params,
        "trace": [{"step": 0, "tool": "degraded", "args": {}, "ok": True, "summary": "关键词解析"}],
        "degraded": True,
        "steps": 0,
        "tool_errors": [],
        "self_check": None,
        "conflicts": [],
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(db: Session, message: str, session_id: Optional[str] = None,
        panel: Optional[dict] = None) -> dict:
    """执行一次 Agent 对话。

    panel 为本轮前端面板参数（可选）：{preferences, main_preferences,
    secondary_preferences, travel_type, days, per_day, hotel_budget}；
    不传时退回会话内的偏好快照。
    """
    text = (message or "").strip()
    sid = session_id or uuid.uuid4().hex
    trace_id = uuid.uuid4().hex[:12]
    history = _SESSIONS.get(sid, [])

    # 偏好快照隔离：本轮优先用 panel，其次用历史快照，绝不从对话文本推断旧偏好
    snapshot = dict(_SNAPSHOTS.get(sid) or {})
    if panel:
        for key, value in panel.items():
            if value not in (None, "", []):
                snapshot[key] = value
        snapshot["origin"] = "panel"
    _SNAPSHOTS[sid] = snapshot

    # 首轮没有面板参数时，用关键词推断一份「临时快照」仅用于冲突预检测
    conflict_snapshot = snapshot
    if not snapshot.get("preferences") and not snapshot.get("travel_type"):
        try:
            cities = ai_agent._get_supported_cities(db)
            inferred, _missing, _signal = ai_agent._fallback_params(text, cities)
            conflict_snapshot = {**snapshot, **{
                k: v for k, v in inferred.items()
                if v not in (None, "", []) and k in ("preferences", "travel_type", "days", "per_day")
            }, "origin": "inferred"}
        except Exception as exc:
            agent_tools._log("conflict_infer_failed", trace_id, error=str(exc))
    conflicts = _detect_conflicts(text, conflict_snapshot)
    agent_tools._log("turn_start", trace_id, session_id=sid, message=text,
                     snapshot=snapshot, conflicts=conflicts)

    if not (settings.DEEPSEEK_API_KEY or "").strip():
        result = _degraded_run(db, text, history)
        history = history + [{"role": "user", "content": text},
                             {"role": "assistant", "content": result["reply"]}]
        _SESSIONS[sid] = history[-MAX_HISTORY:]
        facts = []
        if result.get("route"):
            facts.append(_fact_from_tool("make_route", result.get("params") or {}, result["route"]))
        _remember_facts(sid, facts)
        result["session_id"] = sid
        result["trace_id"] = trace_id
        result["conflicts"] = conflicts
        return result

    system_messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
    snapshot_text = _snapshot_text(snapshot)
    if snapshot_text:
        system_messages.append(
            {"role": "system", "content": "本轮参数快照（以此为准，旧轮偏好不得覆盖）：\n" + snapshot_text}
        )
    facts_text = _facts_text(sid)
    if facts_text:
        system_messages.append(
            {"role": "system", "content": "历史工具事实（以此为准，禁止否认或改写）：\n" + facts_text}
        )
    if conflicts:
        system_messages.append({
            "role": "system",
            "content": "检测到需求冲突：\n%s\n请先用一句话向用户确认是否调整偏好/预算，"
                       "确认前不要调用任何工具。" % "\n".join(c["message"] for c in conflicts),
        })
    messages = system_messages + history + [{"role": "user", "content": text}]

    trace: List[dict] = []
    turn_facts: List[str] = []
    tool_errors: List[str] = []
    route: Optional[dict] = None
    params: dict = {}
    self_check: Optional[dict] = None
    reply = ""
    replan_count = 0
    last_route_args: Optional[dict] = None
    last_critique: Optional[dict] = None

    try:
        for step in range(MAX_STEPS):
            data = _chat(messages, agent_tools.AGENT_TOOLS)
            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError("模型返回空 choices")
            msg = choices[0].get("message") or {}
            messages.append(msg)

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                reply = (msg.get("content") or "").strip()
                break

            for call in tool_calls:
                function = call.get("function") or {}
                name = function.get("name") or ""
                raw_args = function.get("arguments")
                if isinstance(raw_args, dict):
                    args = raw_args
                else:
                    try:
                        args = json.loads(raw_args or "{}")
                    except (TypeError, ValueError):
                        args = {}
                if not isinstance(args, dict):
                    args = {}

                # 服务端兜底：重排时自动把自检里不合格景点并入 exclude_spots，
                # 避免模型只排除一个或忘记排除，导致重排无效
                if name == "make_route" and last_route_args is not None and last_critique:
                    bad = [i.get("target") for i in (last_critique.get("issues") or [])
                           if i.get("code") in ("spot_pref", "spot_missing") and i.get("target")]
                    if bad:
                        merged = sorted(set(list(args.get("exclude_spots") or []) + bad))
                        if merged != list(args.get("exclude_spots") or []):
                            args["exclude_spots"] = merged
                            agent_tools._log("auto_exclude", trace_id, exclude_spots=merged)

                result = _execute_with_timeout(name, args, db, trace_id)
                ok = "error" not in result
                if not ok:
                    tool_errors.append("%s: %s" % (name, result.get("error")))

                # 偏好快照：用本轮工具参数覆盖，供下一轮使用
                if name in ("make_route", "search_spots") and ok:
                    _update_snapshot(sid, args)

                if name == "make_route" and ok:
                    if last_route_args is not None:
                        prev_norm = _norm_route_args(last_route_args)
                        new_norm = _norm_route_args(args)
                        if prev_norm == new_norm:
                            # 参数完全相同：确定性算法必然返回同样路线，标记为无效重排
                            result["replan_noop"] = True
                            result["note"] = (
                                "本次 make_route 参数与上一次完全相同，确定性算法结果不会变化；"
                                "请不要再以相同参数重排，改为调整偏好/天数/每日数量，或如实告知用户"
                            )
                            agent_tools._log("replan_skipped", trace_id,
                                             same_args=args, route=[x.get("name") for x in result.get("route_list") or []])
                        else:
                            replan_count += 1
                            agent_tools._log("replan", trace_id, round=replan_count,
                                             prev_args=last_route_args, new_args=args,
                                             prev_route=[x.get("name") for x in (route or {}).get("route_list") or []])
                    last_route_args = args
                    route = result
                    params = {
                        "target_city": args.get("target_city") or result.get("target_city"),
                        "days": args.get("days") or result.get("days"),
                        "per_day": args.get("per_day") or result.get("per_day"),
                        "preferences": args.get("preferences") or [],
                        "travel_type": args.get("travel_type") or "单人出行",
                        "start_location": args.get("start_location"),
                        # 关键：把重排时的排除名单一并下发，前端复算路线时才能与 Agent 结果一致
                        "exclude_spots": args.get("exclude_spots") or [],
                    }
                    _SNAPSHOTS[sid] = {**(_SNAPSHOTS.get(sid) or {}), **params}

                if name == "critique_route" and ok:
                    self_check = result
                    last_critique = result
                    agent_tools._log("critique_result", trace_id, score=result.get("score"),
                                     breakdown=result.get("score_breakdown"),
                                     issues=result.get("issues"))

                turn_facts.append(_fact_from_tool(name, args, result, trace_id))
                trace.append({
                    "step": step,
                    "tool": name,
                    "args": args,
                    "ok": ok,
                    "summary": (
                        ("共 %s 条" % result.get("count")) if "count" in result
                        else ("score=%s" % result.get("score") if name == "critique_route" and ok
                              else (result.get("error") or "ok"))
                    ),
                })
                print("[agent] step=%d tool=%s ok=%s args=%s" % (step, name, ok, args), flush=True)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id") or "%s-%d" % (name, step),
                    "content": json.dumps(result, ensure_ascii=False)[:TOOL_RESULT_LIMIT],
                })
        else:
            messages.append(
                {"role": "user", "content": "已达到最大工具调用步数，请基于已有信息直接给出最终方案，不要再调用工具。"}
            )
            data = _chat(messages)
            reply = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()

        if not reply:
            reply = "已生成路线，请查看右侧结果。"
    except Exception as exc:
        agent_tools._log("agent_failed", trace_id, error=str(exc))
        result = _degraded_run(db, text, history)
        result["session_id"] = sid
        result["trace_id"] = trace_id
        result["conflicts"] = conflicts
        return result

    history = history + [{"role": "user", "content": text},
                         {"role": "assistant", "content": reply}]
    _SESSIONS[sid] = history[-MAX_HISTORY:]
    _remember_facts(sid, turn_facts)

    agent_tools._log("turn_end", trace_id, session_id=sid, steps=len(trace),
                     replan_count=replan_count, tool_errors=tool_errors,
                     self_check_ok=(self_check or {}).get("ok"),
                     self_check_score=(self_check or {}).get("score"))

    return {
        "session_id": sid,
        "trace_id": trace_id,
        "reply": reply,
        "route": route,
        "params": params,
        "trace": trace,
        "degraded": False,
        "steps": len(trace),
        "tool_errors": tool_errors,
        "self_check": self_check,
        "conflicts": conflicts,
    }


def reset(session_id: str) -> None:
    """清空会话的记忆、事实与偏好快照。"""
    _SESSIONS.pop(session_id, None)
    _FACTS.pop(session_id, None)
    _SNAPSHOTS.pop(session_id, None)
