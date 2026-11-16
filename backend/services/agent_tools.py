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
from services.trip_service import _haversine_km

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
                       near_spot: str = None, radius_km: float = 5,
                       limit: int = HOTEL_LIMIT) -> dict:
    """按城市查在架酒店，可按价格上限、以及距某景点 radius_km 内过滤。"""
    query = db.query(Hotel).filter(Hotel.status == "on_shelf", Hotel.address.contains(city))
    hotels = query.all()
    total_in_city = len(hotels)

    if max_price is not None:
        try:
            cap = float(max_price)
            hotels = [h for h in hotels if float(h.price_per_day or 0) <= cap]
        except (TypeError, ValueError):
            pass

    anchor = None
    note = None
    if near_spot:
        # 用景点名定位锚点；同名多城市时限定在本城市
        spot = (
            db.query(Spot)
            .filter(Spot.city == city, Spot.name.contains(near_spot))
            .filter(Spot.lng.isnot(None), Spot.lat.isnot(None))
            .first()
        )
        if spot is None:
            note = "未找到景点「%s」或该景点缺少坐标，已返回未按距离过滤的结果" % near_spot
        else:
            anchor = (float(spot.lat), float(spot.lng), spot.name)

    result_rows = []
    if anchor:
        try:
            radius = float(radius_km or 5)
        except (TypeError, ValueError):
            radius = 5.0
        for h in hotels:
            if h.lat is None or h.lng is None:
                continue
            dist = _haversine_km(anchor[0], anchor[1], float(h.lat), float(h.lng))
            if dist <= radius:
                result_rows.append((h, round(dist, 2)))
        result_rows.sort(key=lambda item: (item[1], float(item[0].price_per_day or 0)))
    else:
        hotels.sort(key=lambda h: (-float(h.env_score or 0), float(h.price_per_day or 0), h.id))
        result_rows = [(h, None) for h in hotels]

    top = result_rows[: max(1, min(int(limit or HOTEL_LIMIT), 20))]
    payload = {
        "city": city,
        "total_in_city": total_in_city,
        "count": len(top),
        "hotels": [
            {
                "id": h.id,
                "name": h.name,
                "price_per_day": float(h.price_per_day or 0),
                "address": h.address,
                "distance_km": dist,
            }
            for h, dist in top
        ],
    }
    if anchor:
        payload["near_spot"] = anchor[2]
        payload["radius_km"] = float(radius_km or 5)
    if note:
        payload["note"] = note
    return payload


def tool_critique_route(db: Session, spot_names: List[str], city: str = "",
                        preferences: List[str] = None, days: int = None,
                        per_day: int = None) -> dict:
    """对已生成的路线做规则自检：景点真实性、偏好覆盖、数量、跨区跳跃。

    只读检查，不改数据库、不重排路线；返回 issues/suggestions 供模型决定是否重排。
    """
    names = [str(n).strip() for n in (spot_names or []) if str(n or "").strip()]
    if not names:
        return {"error": "需要传入待检查的景点名列表"}

    query = db.query(Spot).filter(Spot.name.in_(names))
    if city:
        query = query.filter(Spot.city == city)
    found = {s.name: s for s in query.all()}

    prefs = [p for p in (preferences or []) if isinstance(p, str) and p.strip()]
    issues = []
    suggestions = []
    checked = []

    missing = [n for n in names if n not in found]
    if missing:
        issues.append("以下景点在数据库中不存在：%s" % "、".join(missing))

    for name in names:
        spot = found.get(name)
        if not spot:
            continue
        hit = [p for p in prefs if p in (spot.tags or "")]
        checked.append({"name": name, "tags": spot.tags, "hit": bool(hit)})
        if prefs and not hit:
            suggestions.append("「%s」不符合偏好（标签：%s）" % (name, spot.tags or "无"))

    if prefs:
        hit_count = sum(1 for c in checked if c["hit"])
        if checked and hit_count == 0:
            issues.append("全部 %d 个景点都不符合偏好 %s" % (len(checked), "/".join(prefs)))
        elif checked and hit_count < len(checked):
            issues.append("%d/%d 个景点不符合偏好 %s" % (len(checked) - hit_count, len(checked), "/".join(prefs)))

    if days and per_day:
        need = int(days) * int(per_day)
        if len(names) < need:
            issues.append("景点数量不足：需要 %d 个，实际 %d 个" % (need, len(names)))

    # 相邻景点跨区跳跃检查（真实坐标，>30km 视为不顺路）
    geo = [(c["name"], found[c["name"]]) for c in checked]
    jumps = []
    for (prev_name, prev), (next_name, nxt) in zip(geo, geo[1:]):
        if prev.lat is None or prev.lng is None or nxt.lat is None or nxt.lng is None:
            continue
        dist = _haversine_km(float(prev.lat), float(prev.lng), float(nxt.lat), float(nxt.lng))
        if dist > 30:
            jumps.append("%s → %s 约 %.1f km" % (prev_name, next_name, dist))
    if jumps:
        issues.append("存在跨区域跳跃：%s" % "；".join(jumps))
        suggestions.append("建议减少远端景点或按区域拆分行程")

    score = 100 - 40 * len([i for i in issues if "不存在" in i]) \
                - 20 * len([i for i in issues if "不符合偏好" in i or "都不符合" in i]) \
                - 15 * len([i for i in issues if "数量不足" in i]) \
                - 15 * len(jumps)
    score = max(0, min(100, score))

    return {
        "city": city or None,
        "score": score,
        "ok": not issues,
        "spot_count": len(names),
        "preference_hits": sum(1 for c in checked if c["hit"]),
        "issues": issues,
        "suggestions": suggestions[:5],
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
            "name": "critique_route",
            "description": "对已生成的路线做自检：景点是否真实存在、是否符合偏好、数量是否够、相邻景点是否跨区太远。生成路线后应调用一次，有 issues 时再决定是否重排。",
            "parameters": {
                "type": "object",
                "properties": {
                    "spot_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "待检查的景点名，按路线顺序传入",
                    },
                    "city": {"type": "string", "description": "城市，可空"},
                    "preferences": {"type": "array", "items": {"type": "string"}},
                    "days": {"type": "integer"},
                    "per_day": {"type": "integer"},
                },
                "required": ["spot_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "查询某城市在架酒店，可限制每晚最高价，也可按「距某景点 radius_km 内」过滤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "max_price": {"type": "number", "description": "每晚最高价，可空"},
                    "near_spot": {
                        "type": "string",
                        "description": "以某个景点为圆心筛选，如 白云山；用户要求“酒店离景点近”时必填",
                    },
                    "radius_km": {
                        "type": "number",
                        "description": "距离半径（公里），默认 5",
                    },
                },
                "required": ["city"],
            },
        },
    },
]

TOOL_NAMES = {"search_spots", "make_route", "search_hotels", "critique_route"}


def execute_tool(name: str, args: dict, db: Session) -> dict:
    """白名单分发；任何工具异常都转成 {"error": ...} 让模型自己纠错。"""
    if name not in TOOL_NAMES:
        return {"error": "未知工具：%s" % name}
    try:
        if name == "search_spots":
            return tool_search_spots(db, **args)
        if name == "make_route":
            return tool_make_route(db, **args)
        if name == "critique_route":
            return tool_critique_route(db, **args)
        return tool_search_hotels(db, **args)
    except TypeError as exc:
        return {"error": "参数不合法：%s" % exc}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # 工具失败不能中断整个 Agent
        return {"error": "工具执行失败：%s" % exc}
