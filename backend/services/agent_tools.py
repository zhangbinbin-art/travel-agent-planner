"""Agent 可调用的只读工具集合。

设计原则：
- 全部只读，第一版不暴露下单/收藏等写操作；
- 每个工具独立 try/except，失败时返回 {"error": ...} 交给模型自行换策略；
- 返回字段做裁剪与条数截断，避免 tool 消息把上下文撑爆。
"""
from typing import List

from sqlalchemy.orm import Session

from models import Hotel, Spot
from schemas.trip import SmartRecommendRequest
from services import trip_service

# 每次返回给模型的景点/酒店条数上限
SPOT_LIMIT = 10
HOTEL_LIMIT = 8


def _spot_brief(spot: Spot) -> dict:
    return {
        "id": spot.id,
        "name": spot.name,
        "city": spot.city,
        "tags": spot.tags,
        "price": float(spot.price or 0),
        "score": float(spot.score or 0),
    }


def tool_search_spots(db: Session, city: str, keyword: str = "", preferences: List[str] = None,
                      limit: int = SPOT_LIMIT) -> dict:
    """按城市查询景点；keyword / preferences 用于二次过滤，返回 total 让模型判断资源是否充足。"""
    rows = db.query(Spot).filter(Spot.city == city).all()
    if not rows:
        return {"city": city, "total": 0, "count": 0, "spots": [], "note": "该城市暂无景点数据"}

    keyword = (keyword or "").strip()
    prefs = [p for p in (preferences or []) if isinstance(p, str) and p.strip()]
    matched = []
    for spot in rows:
        text = "%s %s %s" % (spot.name or "", spot.tags or "", spot.description or "")
        if keyword and keyword not in text:
            continue
        if prefs and not any(p in (spot.tags or "") for p in prefs):
            continue
        matched.append(spot)

    pool = matched or rows
    pool.sort(key=lambda s: (-float(s.score or 0), s.id))
    top = pool[: max(1, min(int(limit or SPOT_LIMIT), 20))]
    return {
        "city": city,
        "total": len(rows),
        "matched": len(matched),
        "count": len(top),
        "spots": [_spot_brief(s) for s in top],
    }


def tool_make_route(db: Session, target_city: str, days: int, per_day: int = 3,
                    preferences: List[str] = None, travel_type: str = "单人出行",
                    start_location: str = None) -> dict:
    """调用现有确定性算法生成路线，返回结构化结果供模型总结。"""
    payload = SmartRecommendRequest(
        target_city=target_city,
        days=days,
        per_day=per_day,
        preferences=preferences or [],
        travel_type=travel_type or "单人出行",
        start_location=start_location,
    )
    res = trip_service.smart_recommend(db, payload)
    day_plans = [
        {"day": d.get("day"), "spots": d.get("spot_names") or []}
        for d in (res.get("day_plans") or [])
    ]
    return {
        "target_city": target_city,
        "days": days,
        "per_day": per_day,
        "route_list": [
            {"name": s.get("name"), "price": s.get("price")} for s in (res.get("route_list") or [])
        ],
        "day_plans": day_plans,
        "total_distance": res.get("total_distance"),
        "tips": res.get("tips"),
    }


def tool_search_hotels(db: Session, city: str, max_price: float = None,
                       limit: int = HOTEL_LIMIT) -> dict:
    """按城市查在架酒店，可按价格上限过滤。"""
    query = db.query(Hotel).filter(Hotel.status == "on_shelf", Hotel.address.contains(city))
    hotels = query.all()
    if max_price is not None:
        try:
            cap = float(max_price)
            hotels = [h for h in hotels if float(h.price_per_day or 0) <= cap]
        except (TypeError, ValueError):
            pass
    hotels.sort(key=lambda h: (-float(h.env_score or 0), float(h.price_per_day or 0), h.id))
    top = hotels[: max(1, min(int(limit or HOTEL_LIMIT), 20))]
    return {
        "city": city,
        "total": len(hotels),
        "count": len(top),
        "hotels": [
            {
                "id": h.id,
                "name": h.name,
                "price_per_day": float(h.price_per_day or 0),
                "address": h.address,
            }
            for h in top
        ],
    }


# 供模型使用的工具声明（JSON Schema）
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_spots",
            "description": "查询某城市的真实景点数据，可按关键词或偏好过滤；用于确认资源是否充足、有哪些景点可选。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，例如 广州"},
                    "keyword": {"type": "string", "description": "关键词，如 山、博物馆，可空"},
                    "preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "偏好标签，如 自然风光、徒步登山",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_route",
            "description": "按城市与天数生成完整旅行路线（内部使用确定性算法，返回景点顺序、每天分组、总里程与提示）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_city": {"type": "string", "description": "目的地城市"},
                    "days": {"type": "integer", "minimum": 1, "maximum": 10},
                    "per_day": {"type": "integer", "minimum": 1, "maximum": 4},
                    "preferences": {"type": "array", "items": {"type": "string"}},
                    "travel_type": {
                        "type": "string",
                        "enum": ["单人出行", "情侣出行", "家庭亲子", "老年休闲"],
                    },
                    "start_location": {"type": "string", "description": "出发城市，可空"},
                },
                "required": ["target_city", "days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "查询某城市在架酒店，可限制每晚最高价。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "max_price": {"type": "number", "description": "每晚最高价，可空"},
                },
                "required": ["city"],
            },
        },
    },
]

TOOL_NAMES = {"search_spots", "make_route", "search_hotels"}


def execute_tool(name: str, args: dict, db: Session) -> dict:
    """白名单分发；任何工具异常都转成 {"error": ...} 让模型自己纠错。"""
    if name not in TOOL_NAMES:
        return {"error": "未知工具：%s" % name}
    try:
        if name == "search_spots":
            return tool_search_spots(db, **args)
        if name == "make_route":
            return tool_make_route(db, **args)
        return tool_search_hotels(db, **args)
    except TypeError as exc:
        return {"error": "参数不合法：%s" % exc}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # 工具失败不能中断整个 Agent
        return {"error": "工具执行失败：%s" % exc}
