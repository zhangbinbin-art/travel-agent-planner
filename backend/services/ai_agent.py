"""DeepSeek Function-Calling 需求解析层。

职责边界：
- 只把一句中文需求解析为 smart_recommend 参数，**不**调用 trip_service 生成路线；
- 所有网络、JSON 解析、参数校验都做异常隔离，任何异常都不能向上抛成 500；
- 未配置 DEEPSEEK_API_KEY / 调用失败 / 无 tool_call 时，自动降级为纯 Python 关键词解析。

DeepSeek 接口要点（2026-11 官方文档）：
- 端点 https://api.deepseek.com/chat/completions（无 /v1）
- 默认开启思考模式，必须显式传顶层 "thinking": {"type": "disabled"}
- 返回 choices[0].message.tool_calls 为数组，function.arguments 是 JSON 字符串
"""
import json
import re
from typing import List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from models import Spot

# 偏好标签白名单（与前端表单/服务层保持一致，模型只能从这里选）
PREF_WHITELIST = ["自然风光", "人文古迹", "美食探店", "游乐乐园", "城市逛街", "徒步登山", "海滨海岛", "亲子出游"]
# 出行人群白名单
TRAVEL_TYPES = ["单人出行", "情侣出行", "家庭亲子", "老年休闲"]

# 关键词兜底用的常见说法 -> 白名单标签；仅用于模型不可用时提高召回
PREF_ALIASES = [
    ("自然风光", "自然风光"), ("自然", "自然风光"), ("风景", "自然风光"), ("山水", "自然风光"),
    ("人文古迹", "人文古迹"), ("古迹", "人文古迹"), ("历史", "人文古迹"), ("人文", "人文古迹"),
    ("美食探店", "美食探店"), ("美食", "美食探店"), ("小吃", "美食探店"),
    ("游乐乐园", "游乐乐园"), ("乐园", "游乐乐园"), ("游乐", "游乐乐园"),
    ("城市逛街", "城市逛街"), ("逛街", "城市逛街"), ("购物", "城市逛街"),
    ("徒步登山", "徒步登山"), ("登山", "徒步登山"), ("徒步", "徒步登山"), ("爬山", "徒步登山"),
    ("海滨海岛", "海滨海岛"), ("海岛", "海滨海岛"), ("海滨", "海滨海岛"), ("海边", "海滨海岛"),
    ("亲子出游", "亲子出游"), ("亲子", "亲子出游"),
]

PLAN_SYSTEM_PROMPT = (
    "你是国内旅行规划助手。请把用户的自然语言需求解析为 smart_recommend 工具参数。"
    "只提取用户明确表达的信息；目的地城市必须填真实城市名；"
    "偏好只能从给定枚举中选择，用户没提到的偏好不要编造；"
    "天数、每日景点数无法确定时不要猜测。"
)

EXPLAIN_SYSTEM_PROMPT = (
    "你是国内旅行行程解说助手；只依据给定数据；"
    "不得编造不存在的景点或价格；150~250 字；纯文本中文；不要 markdown；"
    "若有 tips 字段，用它解释“为什么景点比设置数量少”。"
)

# 暴露给模型的工具声明：字段越少，模型幻觉越少
PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "smart_recommend",
        "description": "把用户的自然语言旅行需求解析为智能推荐参数。",
        "parameters": {
            "type": "object",
            "properties": {
                "target_city": {
                    "type": "string",
                    "description": "目的地城市，例如 广州",
                },
                "days": {
                    "type": "integer",
                    "description": "游玩天数，范围 1~10",
                    "minimum": 1,
                    "maximum": 10,
                },
                "per_day": {
                    "type": "integer",
                    "description": "每日游玩景点数量，范围 1~4，默认 3",
                    "minimum": 1,
                    "maximum": 4,
                },
                "preferences": {
                    "type": "array",
                    "description": "偏好标签，只能从枚举中选择",
                    "items": {"type": "string", "enum": PREF_WHITELIST},
                },
                "travel_type": {
                    "type": "string",
                    "description": "出行人群类型",
                    "enum": TRAVEL_TYPES,
                },
                "start_location": {
                    "type": "string",
                    "description": "出发城市，可空",
                },
            },
            "required": ["target_city", "days"],
        },
    },
}


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def _has_key() -> bool:
    """是否配置了 DeepSeek Key。"""
    return bool((settings.DEEPSEEK_API_KEY or "").strip())


def _chat_url() -> str:
    """拼接 chat/completions 地址，兼容 base_url 末尾带斜杠。"""
    return settings.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"


def _headers() -> dict:
    return {
        "Authorization": "Bearer %s" % settings.DEEPSEEK_API_KEY,
        "Content-Type": "application/json",
    }


def _default_params() -> dict:
    """兜底参数：字段顺序与 SmartRecommendRequest 子集一致。"""
    return {
        "target_city": "",
        "days": 2,
        "per_day": 3,
        "preferences": [],
        "travel_type": TRAVEL_TYPES[0],
        "start_location": None,
    }


def _clamp_int(value, low: int, high: int, default: int) -> int:
    """把任意输入转成区间内的整数，失败返回默认值。"""
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return default
    if number < low:
        return low
    if number > high:
        return high
    return number


def _get_supported_cities(db: Session) -> List[str]:
    """读取数据库支持的城市列表；查询失败时返回空列表而不是抛异常。"""
    try:
        rows = db.query(Spot.city).distinct().all()
    except Exception as exc:
        print("[ai] 城市列表查询失败，降级=%s" % exc, flush=True)
        return []
    cities: List[str] = []
    for row in rows:
        city = (row[0] or "").strip()
        if city and city not in cities:
            cities.append(city)
    return cities


def _resolve_city(value, cities: List[str]) -> Optional[str]:
    """把模型/关键词给出的城市对齐到数据库城市。

    先精确匹配，再双向包含匹配（"广州市" -> "广州"）。
    DB 城市列表为空（查询失败）时，直接采用原值兜底，避免整条链路失效。
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not cities:
        return text
    for city in cities:
        if city == text:
            return city
    for city in sorted(cities, key=len, reverse=True):
        if city and (city in text or text in city):
            return city
    return None


def _match_city_in_text(text: str, cities: List[str]) -> Optional[str]:
    """在文本中匹配城市名，长城市名优先（如先匹配"呼和浩特"再匹配"浩特"）。"""
    if not text:
        return None
    for city in sorted(cities, key=len, reverse=True):
        if city and city in text:
            return city
    return None


def _clean_preferences(value) -> List[str]:
    """只保留白名单标签，去重并保持原顺序。"""
    if not isinstance(value, (list, tuple)):
        return []
    result: List[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        tag = item.strip()
        if tag in PREF_WHITELIST and tag not in result:
            result.append(tag)
    return result


# ---------------------------------------------------------------------------
# 参数校验（不信任模型输出）
# ---------------------------------------------------------------------------

def _sanitize_params(raw: dict, cities: List[str]) -> Tuple[dict, List[str]]:
    """把模型返回的原始参数清洗成可安全下发的 6 字段结构。"""
    missing: List[str] = []

    target_city = _resolve_city(raw.get("target_city"), cities)
    if not target_city:
        missing.append("target_city")
        target_city = ""

    travel_type = raw.get("travel_type")
    if travel_type not in TRAVEL_TYPES:
        travel_type = TRAVEL_TYPES[0]

    start_location = raw.get("start_location")
    if isinstance(start_location, str):
        start_location = start_location.strip() or None
    else:
        start_location = None

    params = {
        "target_city": target_city,
        "days": _clamp_int(raw.get("days"), 1, 10, 2),
        "per_day": _clamp_int(raw.get("per_day"), 1, 4, 3),
        "preferences": _clean_preferences(raw.get("preferences")),
        "travel_type": travel_type,
        "start_location": start_location,
    }
    return params, missing


# ---------------------------------------------------------------------------
# 关键词兜底（无 Key / 调用失败时）
# ---------------------------------------------------------------------------

CN_DIGITS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_number(token: str) -> int:
    """把「三」「十」「十二」「两」这类中文数字转成整数，无法识别返回 0。"""
    token = (token or "").strip()
    if not token:
        return 0
    if "十" in token:
        left, _, right = token.partition("十")
        tens = CN_DIGITS.get(left, 1) if left else 1
        ones = CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    return CN_DIGITS.get(token, 0)


def _fallback_params(text: str, cities: List[str]) -> Tuple[dict, List[str], bool]:
    """纯 Python 关键词解析，返回 (params, missing, 是否识别到任何信号)。"""
    has_signal = False

    city = _match_city_in_text(text, cities)
    if city:
        has_signal = True

    days = 2
    day_match = re.search(r"(\d+)\s*天", text)
    if day_match:
        days = _clamp_int(day_match.group(1), 1, 10, 2)
        has_signal = True
    else:
        # 兜底支持中文数字天数：「玩三天」「两天一夜」
        cn_match = re.search(r"([一二两三四五六七八九十]{1,3})\s*天", text)
        if cn_match:
            days = _clamp_int(_cn_number(cn_match.group(1)), 1, 10, 2)
            has_signal = True

    # 偏好：按在文本中出现的先后顺序收集
    found = {}
    for tag in PREF_WHITELIST:
        index = text.find(tag)
        if index >= 0:
            found[tag] = index
    for keyword, tag in PREF_ALIASES:
        index = text.find(keyword)
        if index >= 0 and tag not in found:
            found[tag] = index
    preferences = [tag for tag, _ in sorted(found.items(), key=lambda item: item[1])]
    if preferences:
        has_signal = True

    # 出行人群：爸妈/老人优先于亲子/情侣
    travel_type = TRAVEL_TYPES[0]
    if any(keyword in text for keyword in ("爸妈", "父母", "老人", "长辈", "老年")):
        travel_type = "老年休闲"
        has_signal = True
    elif any(keyword in text for keyword in ("带孩子", "亲子", "小孩", "宝宝", "孩子")):
        travel_type = "家庭亲子"
        has_signal = True
    elif any(keyword in text for keyword in ("情侣", "两人", "二人", "女朋友", "男朋友", "蜜月")):
        travel_type = "情侣出行"
        has_signal = True

    # 出发地：从"从XX出发"中提取
    start_location = None
    start_match = re.search(r"从\s*([\u4e00-\u9fa5]{1,12})\s*出发", text)
    if start_match:
        start_location = start_match.group(1).strip() or None
        if start_location:
            has_signal = True

    missing: List[str] = []
    if not city:
        missing.append("target_city")

    params = {
        "target_city": city or "",
        "days": days,
        "per_day": 3,
        "preferences": preferences,
        "travel_type": travel_type,
        "start_location": start_location,
    }
    return params, missing, has_signal


# ---------------------------------------------------------------------------
# DeepSeek 调用
# ---------------------------------------------------------------------------

def _request_plan(message: str) -> Optional[dict]:
    """调用 DeepSeek 获取 smart_recommend tool_call 参数；失败返回 None。"""
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        "tools": [PLAN_TOOL],
        "tool_choice": "auto",
        # 关闭思考模式，保证工具路由稳定（顶层字段，不是 extra_body）
        "thinking": {"type": "disabled"},
    }
    with httpx.Client(timeout=settings.DEEPSEEK_TIMEOUT) as client:
        response = client.post(_chat_url(), json=payload, headers=_headers())
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        return None
    message_obj = choices[0].get("message") or {}
    tool_calls = message_obj.get("tool_calls") or []
    for call in tool_calls:
        function = call.get("function") or {}
        if function.get("name") != "smart_recommend":
            continue
        arguments = function.get("arguments")
        if isinstance(arguments, dict):
            args = arguments
        else:
            try:
                args = json.loads(arguments or "{}")
            except (ValueError, TypeError):
                return None
        if not isinstance(args, dict):
            return None
        print("[ai] 模型返回 tool_call 参数=%s" % args, flush=True)
        return args
    return None


def _request_explain(message: str, route_summary: dict) -> Optional[str]:
    """调用 DeepSeek 生成中文行程说明；失败或空内容返回 None。"""
    user_content = "用户原始需求：%s\n\n路线数据（JSON）：%s" % (
        message,
        json.dumps(route_summary, ensure_ascii=False),
    )
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "thinking": {"type": "disabled"},
    }
    with httpx.Client(timeout=settings.DEEPSEEK_TIMEOUT) as client:
        response = client.post(_chat_url(), json=payload, headers=_headers())
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        return None
    message_obj = choices[0].get("message") or {}
    content = message_obj.get("content")
    if not isinstance(content, str):
        return None
    content = content.strip()
    if not content:
        return None
    print("[ai] 模型返回行程说明 长度=%s" % len(content), flush=True)
    return content


# ---------------------------------------------------------------------------
# 对外入口
# ---------------------------------------------------------------------------

def _compose_reply(params: dict, missing: List[str], cities: List[str]) -> str:
    """组装"已识别：城市 · 天数 · 偏好 · 人群"格式的回复。"""
    city = params.get("target_city") or "未识别目的地"
    preferences = params.get("preferences") or []
    pref_text = "/".join(preferences) if preferences else "未指定偏好"
    parts = [
        city,
        "%d 天" % params.get("days", 2),
        pref_text,
        params.get("travel_type") or TRAVEL_TYPES[0],
    ]
    reply = "已识别：" + " · ".join(parts)
    reply += _missing_hint(missing, cities)
    return reply


def _missing_hint(missing: List[str], cities: List[str]) -> str:
    """把缺失项转成中文提示；城市缺失时列出最多 5 个支持城市。"""
    hints: List[str] = []
    if "target_city" in missing:
        if cities:
            hints.append("未识别目的地，支持城市如：%s" % "、".join(cities[:5]))
        else:
            hints.append("未识别目的地，请手动选择城市")
    if not hints:
        return ""
    return "；" + "；".join(hints)


def plan_from_message(db: Session, message: str) -> dict:
    """解析一句中文需求，返回 AIPlanResponse 兼容字典，永不抛异常。"""
    text = (message or "").strip()
    cities = _get_supported_cities(db)

    raw: Optional[dict] = None
    degraded = True
    if _has_key():
        try:
            raw = _request_plan(text)
            if raw is not None:
                degraded = False
        except Exception as exc:
            print("[ai] 调用失败，降级=%s" % exc, flush=True)
            raw = None
    else:
        print("[ai] 未配置 DEEPSEEK_API_KEY，使用关键词兜底解析", flush=True)

    # 模型返回成功：清洗后直接下发
    if raw is not None:
        try:
            params, missing = _sanitize_params(raw, cities)
            return {
                "ok": True,
                "degraded": degraded,
                "reply": _compose_reply(params, missing, cities),
                "missing": missing,
                "params": params,
            }
        except Exception as exc:
            print("[ai] 参数校验失败，降级=%s" % exc, flush=True)

    # 关键词兜底（其自身也包一层，保证永远有可用结果）
    try:
        params, missing, has_signal = _fallback_params(text, cities)
    except Exception as exc:
        print("[ai] 关键词兜底失败，降级=%s" % exc, flush=True)
        params, missing, has_signal = _default_params(), ["target_city"], False

    resolved = bool(params.get("target_city"))
    if has_signal or resolved:
        reply = "AI 解析暂不可用，已按关键词填入可识别信息，请手动确认后生成"
    else:
        reply = "未能从描述中识别有效信息，请手动填写表单后生成行程"
    reply += _missing_hint(missing, cities)
    return {
        "ok": bool(has_signal or resolved),
        "degraded": True,
        "reply": reply,
        "missing": missing,
        "params": params,
    }


def explain_route(message: str, route_summary: dict) -> dict:
    """对已有路线生成中文解说，返回 AIExplainResponse 兼容字典，永不抛异常。"""
    text = (message or "").strip()
    if not _has_key():
        print("[ai] 未配置 DEEPSEEK_API_KEY，跳过行程说明", flush=True)
        return {"ok": False, "degraded": True, "note": None}

    note: Optional[str] = None
    try:
        note = _request_explain(text, route_summary)
    except Exception as exc:
        print("[ai] 调用失败，降级=%s" % exc, flush=True)
        note = None

    if not note:
        return {"ok": False, "degraded": True, "note": None}
    return {"ok": True, "degraded": False, "note": note}


def default_plan_response() -> dict:
    """接口层兜底：AI 层意外异常时返回的可用载荷。"""
    return {
        "ok": False,
        "degraded": True,
        "reply": "AI 服务暂时不可用，请手动填写表单后生成行程",
        "missing": ["target_city"],
        "params": _default_params(),
    }


def default_explain_response() -> dict:
    """接口层兜底：行程说明不可用。"""
    return {"ok": False, "degraded": True, "note": None}
