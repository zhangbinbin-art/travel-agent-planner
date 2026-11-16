"""多步 Agent 运行器：ReAct 式「模型 → 工具 → 观察 → 再决策」循环。

与单轮 /ai/plan 的区别：
- 模型可先查景点、再决定参数、最后生成路线；
- 工具结果以 role=tool 回填 messages，模型据此调整策略；
- 最多 MAX_STEPS 步，超步数强制收尾，避免死循环与成本失控。

无 DEEPSEEK_API_KEY 或模型不可用时，退化为「关键词解析 + 确定性路线」，接口仍可用。
"""
import json
import uuid
from typing import Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from services import ai_agent, agent_tools

MAX_STEPS = 5
# 单次会话保留的消息条数（含 tool 消息），防止上下文无限增长
MAX_HISTORY = 20
# tool 结果回填时的字符上限
TOOL_RESULT_LIMIT = 4000

AGENT_SYSTEM_PROMPT = (
    "你是国内旅行规划 Agent。你可以调用工具查询景点、生成路线、查询酒店。"
    "规则："
    "1) 涉及具体城市时，先用 search_spots 查看真实景点数量，再调用 make_route；"
    "2) 用户提到预算或住宿时，用 search_hotels；"
    "3) 偏好只能使用：自然风光、人文古迹、美食探店、游乐乐园、城市逛街、徒步登山、海滨海岛、亲子出游；"
    "4) 工具返回的景点/价格必须原样引用，不得编造；"
    "5) 路线生成后，用 150~250 字中文总结（不要 markdown），若 tips 说明景点不足，要如实解释；"
    "6) 与旅行无关的请求直接拒绝；"
    "7) 不要重复调用同一个工具和同一组参数。"
)

# 进程内会话记忆：session_id -> messages（不含 system）
_SESSIONS: Dict[str, List[dict]] = {}


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


def _extract_route(trace: List[dict], route: Optional[dict]) -> Optional[dict]:
    """返回最后一次 make_route 的完整结果（trace 里只存摘要）。"""
    return route


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
    }


def run(db: Session, message: str, session_id: Optional[str] = None) -> dict:
    """执行一次 Agent 对话，返回可直接下发给前端的字典。"""
    text = (message or "").strip()
    sid = session_id or uuid.uuid4().hex
    history = _SESSIONS.get(sid, [])

    if not (settings.DEEPSEEK_API_KEY or "").strip():
        result = _degraded_run(db, text, history)
        history = history + [{"role": "user", "content": text},
                             {"role": "assistant", "content": result["reply"]}]
        _SESSIONS[sid] = history[-MAX_HISTORY:]
        result["session_id"] = sid
        return result

    messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": text}
    ]
    trace: List[dict] = []
    route: Optional[dict] = None
    params: dict = {}
    reply = ""

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

                result = agent_tools.execute_tool(name, args, db)
                ok = "error" not in result
                if name == "make_route" and ok:
                    route = result
                    params = {
                        "target_city": args.get("target_city") or result.get("target_city"),
                        "days": args.get("days") or result.get("days"),
                        "per_day": args.get("per_day") or result.get("per_day"),
                        "preferences": args.get("preferences") or [],
                        "travel_type": args.get("travel_type") or "单人出行",
                        "start_location": args.get("start_location"),
                    }
                trace.append(
                    {
                        "step": step,
                        "tool": name,
                        "args": args,
                        "ok": ok,
                        "summary": (
                            ("共 %s 条" % result.get("count")) if "count" in result
                            else (result.get("error") or "ok")
                        ),
                    }
                )
                print("[agent] step=%d tool=%s ok=%s args=%s" % (step, name, ok, args), flush=True)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id") or "%s-%d" % (name, step),
                        "content": json.dumps(result, ensure_ascii=False)[:TOOL_RESULT_LIMIT],
                    }
                )
        else:
            # 超出步数：让模型基于已有信息直接收尾
            messages.append(
                {"role": "user", "content": "已达到最大工具调用步数，请基于已有信息直接给出最终方案，不要再调用工具。"}
            )
            data = _chat(messages)
            reply = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            reply = reply.strip()

        if not reply:
            reply = "已生成路线，请查看右侧结果。"
    except Exception as exc:
        print("[agent] 运行失败，降级=%s" % exc, flush=True)
        result = _degraded_run(db, text, history)
        result["session_id"] = sid
        return result

    history = history + [{"role": "user", "content": text},
                         {"role": "assistant", "content": reply}]
    _SESSIONS[sid] = history[-MAX_HISTORY:]

    return {
        "session_id": sid,
        "reply": reply,
        "route": _extract_route(trace, route),
        "params": params,
        "trace": trace,
        "degraded": False,
        "steps": len(trace),
    }


def reset(session_id: str) -> None:
    """清空某个会话的记忆。"""
    _SESSIONS.pop(session_id, None)
