"""Agent 可调用的只读工具集合（v1.2 增量优化版）。

设计原则：
- 全部只读，不写数据库；
- 每个工具独立 try/except，失败时返回 {"error": ...} 交给模型换策略；
- 返回字段做裁剪与条数截断，避免 tool 消息撑爆上下文；
- 所有新增参数均为可选，旧调用方式保持兼容；
- day_preferences 为 v1.2 预留字段，当前仅透传/记录，不参与计算。
"""
import json
import time
from typing import List, Optional

from sqlalchemy.orm import Session

from models import Hotel, Spot
from schemas.trip import SmartRecommendRequest
from services import trip_service
from services.trip_service import _haversine_km

# 每次返回给模型的景点/酒店条数上限
SPOT_LIMIT = 10
HOTEL_LIMIT = 8
# 偏好命中后仍保留的备选条数（不强制过滤）
SPOT_BACKUP = 4

# 距离阈值：球面距离，仅作参考（不等于路网通勤距离）
DIST_SOFT_KM = 30.0
DIST_SEVERE_KM = 60.0

# 分项满分
SCORE_VALIDITY = 40
SCORE_PREFERENCE = 35
SCORE_COUNT = 15
SCORE_DISTANCE = 10


def _log(event: str, trace_id: Optional[str] = None, **fields) -> None:
    """统一结构化日志：单行 JSON，便于 grep 与复现。"""
    payload = {"event": event, "trace_id": trace_id or "-", "ts": round(time.time(), 3)}
    payload.update(fields)
    print("[agent-trace] %s" % json.dumps(payload, ensure_ascii=False), flush=True)


def _spot_brief(spot: Spot) -> dict:
    return {
        "id": spot.id,
        "name": spot.name,
        "city": spot.city,
        "tags": spot.tags,
        "price": float(spot.price or 0),
        "score": float(spot.score or 0),
    }


def _pref_weight(tags: str, main_prefs: List[str], secondary_prefs: List[str]) -> float:
    """单景点偏好权重：命中主偏好 1.0，仅命中次要偏好 0.5，否则 0。"""
    text = tags or ""
    if any(p in text for p in main_prefs):
        return 1.0
    if any(p in text for p in secondary_prefs):
        return 0.5
    return 0.0


def tool_search_spots(db: Session, city: str, keyword: str = "", preferences: List[str] = None,
                      main_preferences: List[str] = None, secondary_preferences: List[str] = None,
                      day_preferences: List[List[str]] = None, limit: int = SPOT_LIMIT) -> dict:
    """按城市查景点：偏好只影响排序优先级，保留少量备选，不做硬过滤。

    - preferences：兼容旧参数，等同主偏好；
    - main_preferences / secondary_preferences：主/次偏好，主偏好权重更高；
    - day_preferences：v1.2 预留（逐日偏好），当前不参与计算，仅回显。
    """
    rows = db.query(Spot).filter(Spot.city == city).all()
    if not rows:
        return {"city": city, "total": 0, "count": 0, "spots": [], "note": "该城市暂无景点数据"}

    main_prefs = [p for p in (main_preferences or preferences or []) if isinstance(p, str) and p.strip()]
    secondary_prefs = [p for p in (secondary_preferences or []) if isinstance(p, str) and p.strip()]
    keyword = (keyword or "").strip()

    weighted = []
    for spot in rows:
        text = "%s %s %s" % (spot.name or "", spot.tags or "", spot.description or "")
        if keyword and keyword not in text:
            continue
        weight = _pref_weight(spot.tags, main_prefs, secondary_prefs)
        weighted.append((weight, float(spot.score or 0), spot))

    # 主偏好命中 > 次要偏好命中 > 备选；同权重按评分降序
    weighted.sort(key=lambda item: (-item[0], -item[1], item[2].id))

    has_pref = bool(main_prefs or secondary_prefs)
    if has_pref:
        hits = [item for item in weighted if item[0] > 0]
        backups = [item for item in weighted if item[0] <= 0]
        chosen = hits[: max(1, min(int(limit or SPOT_LIMIT), 20))] + backups[:SPOT_BACKUP]
    else:
        chosen = weighted[: max(1, min(int(limit or SPOT_LIMIT), 20))]

    spots = []
    for weight, _score, spot in chosen:
        brief = _spot_brief(spot)
        brief["preference_weight"] = weight  # 1.0 主偏好 / 0.5 次偏好 / 0 备选
        spots.append(brief)

    return {
        "city": city,
        "total": len(rows),
        "matched": len(weighted),
        "count": len(spots),
        "preference_hits": sum(1 for s in spots if s["preference_weight"] > 0),
        "backup_count": sum(1 for s in spots if s["preference_weight"] == 0),
        "day_preferences_reserved": day_preferences or None,
        "spots": spots,
    }


def tool_make_route(db: Session, target_city: str, days: int, per_day: int = 3,
                    preferences: List[str] = None, travel_type: str = "单人出行",
                    start_location: str = None, day_preferences: List[List[str]] = None,
                    trace_id: Optional[str] = None) -> dict:
    """调用现有确定性算法生成路线；day_preferences 为 v1.2 预留（当前不生效）。"""
    if day_preferences:
        _log("make_route.day_preferences_ignored", trace_id, target_city=target_city,
             day_preferences=day_preferences)
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


def _issue(code: str, level: str, category: str, target: str, message: str) -> dict:
    """统一问题结构：level=severe/warn；category=no_resource/route_limit/other。"""
    return {"code": code, "level": level, "category": category, "target": target, "message": message}


def _check_hotels(hotel_list, hotel_budget, hotel_tags, hotel_max_radius) -> List[dict]:
    """酒店约束校验：预算 / 标签 / 距圆心半径；只读传入列表，不查库。"""
    issues = []
    for hotel in hotel_list or []:
        if not isinstance(hotel, dict):
            continue
        name = hotel.get("name") or "未知酒店"
        price = hotel.get("price_per_day")
        if hotel_budget is not None and price is not None:
            try:
                if float(price) > float(hotel_budget):
                    issues.append(_issue(
                        "hotel_budget", "warn", "no_resource", name,
                        "「%s」每晚 %s 元，超出预算 %s 元；建议放宽预算或换更经济的酒店"
                        % (name, price, hotel_budget),
                    ))
            except (TypeError, ValueError):
                pass
        if hotel_tags:
            tag_text = "%s %s" % (hotel.get("tags") or "", hotel.get("facilities") or "")
            missing = [t for t in hotel_tags if t not in tag_text]
            if missing:
                issues.append(_issue(
                    "hotel_tags", "warn", "no_resource", name,
                    "「%s」未标注所需设施：%s" % (name, "、".join(missing)),
                ))
        dist = hotel.get("distance_km")
        if hotel_max_radius is not None and dist is not None:
            try:
                if float(dist) > float(hotel_max_radius):
                    issues.append(_issue(
                        "hotel_radius", "severe", "no_resource", name,
                        "「%s」距圆心 %.2f km，超出 %s km 半径" % (name, float(dist), hotel_max_radius),
                    ))
            except (TypeError, ValueError):
                pass
    return issues


def tool_critique_route(db: Session, spot_names: List[str], city: str = "",
                        preferences: List[str] = None, main_preferences: List[str] = None,
                        secondary_preferences: List[str] = None, days: int = None,
                        per_day: int = None, hotel_list: List[dict] = None,
                        hotel_budget: float = None, hotel_tags: List[str] = None,
                        hotel_max_radius: float = None,
                        day_preferences: List[List[str]] = None,
                        trace_id: Optional[str] = None) -> dict:
    """路线自检（只读）。

    评分：景点真实性 40 + 偏好覆盖 35（主偏好权重更高）+ 数量 15 + 距离 10，
    酒店问题在总分上额外扣分。距离不做一刀切：>=30km 提醒，>=60km 视为严重，
    并注明「球面距离 ≠ 路网通勤耗时」。
    """
    names = [str(n).strip() for n in (spot_names or []) if str(n or "").strip()]
    if not names:
        return {"error": "需要传入待检查的景点名列表"}

    main_prefs = [p for p in (main_preferences or preferences or []) if isinstance(p, str) and p.strip()]
    secondary_prefs = [p for p in (secondary_preferences or []) if isinstance(p, str) and p.strip()]

    query = db.query(Spot).filter(Spot.name.in_(names))
    if city:
        query = query.filter(Spot.city == city)
    found = {s.name: s for s in query.all()}

    issues: List[dict] = []

    # ① 景点真实性（40 分）
    missing = [n for n in names if n not in found]
    actual = [n for n in names if n in found]
    validity_score = SCORE_VALIDITY * (len(actual) / len(names))
    for name in missing:
        issues.append(_issue(
            "spot_missing", "severe", "no_resource", name,
            "库里查不到景点「%s」，可能是名称不一致或数据缺失" % name,
        ))

    # ② 偏好覆盖（35 分）：主偏好 1.0 / 次要偏好 0.5
    checked = []
    for name in actual:
        spot = found[name]
        weight = _pref_weight(spot.tags, main_prefs, secondary_prefs)
        checked.append({"name": name, "tags": spot.tags or "", "weight": weight})
        if (main_prefs or secondary_prefs) and weight == 0:
            issues.append(_issue(
                "spot_pref", "warn", "route_limit", name,
                "「%s」标签为 %s，不符合当前偏好 %s"
                % (name, spot.tags or "无", "/".join(main_prefs + secondary_prefs)),
            ))

    if checked and (main_prefs or secondary_prefs):
        coverage = sum(c["weight"] for c in checked) / len(checked)
    else:
        coverage = 1.0 if not (main_prefs or secondary_prefs) else 0.0
    preference_score = SCORE_PREFERENCE * min(1.0, coverage)

    main_hits = sum(1 for c in checked if any(p in c["tags"] for p in main_prefs))
    secondary_hits = sum(1 for c in checked if c["weight"] == 0.5)
    if main_prefs and checked and main_hits == 0:
        issues.append(_issue(
            "main_pref_missing", "severe", "route_limit", "整条路线",
            "路线里没有任何景点命中主偏好 %s，建议更换目的地或放宽偏好" % "/".join(main_prefs),
        ))

    # ③ 景点数量（15 分）
    shortfall = 0
    if days and per_day:
        need = int(days) * int(per_day)
        shortfall = max(0, need - len(names))
        count_score = SCORE_COUNT * min(1.0, len(names) / need)
        if shortfall:
            issues.append(_issue(
                "count_short", "warn", "route_limit", "整条路线",
                "景点数量不足：需要 %d 个，实际 %d 个；城市里符合偏好的景点可能不够"
                % (need, len(names)),
            ))
    else:
        count_score = SCORE_COUNT

    # ④ 距离合理性（10 分）：球面距离仅作参考
    jumps, severe_jumps = [], []
    for prev, nxt in zip(checked, checked[1:]):
        prev_name, next_name = prev["name"], nxt["name"]
        pa, nb = found[prev_name], found[next_name]
        if pa.lat is None or pa.lng is None or nb.lat is None or nb.lng is None:
            continue
        dist = _haversine_km(float(pa.lat), float(pa.lng), float(nb.lat), float(nb.lng))
        if dist >= DIST_SEVERE_KM:
            severe_jumps.append((prev_name, next_name, dist))
            issues.append(_issue(
                "distance_severe", "severe", "route_limit", "%s→%s" % (prev_name, next_name),
                "【严重距离问题】%s 到 %s 球面距离约 %.1f km，跨区域明显，建议减少远端景点"
                % (prev_name, next_name, dist),
            ))
        elif dist >= DIST_SOFT_KM:
            jumps.append((prev_name, next_name, dist))
            issues.append(_issue(
                "distance_warn", "warn", "route_limit", "%s→%s" % (prev_name, next_name),
                "【仅距离偏大提醒】%s 到 %s 球面距离约 %.1f km，实际通勤请以路网为准"
                % (prev_name, next_name, dist),
            ))
    distance_score = max(0.0, SCORE_DISTANCE - 2.5 * len(jumps) - 5.0 * len(severe_jumps))

    # ⑤ 酒店约束：并入总分扣分
    hotel_issues = _check_hotels(hotel_list, hotel_budget, hotel_tags, hotel_max_radius)
    issues.extend(hotel_issues)

    validity_score = round(validity_score, 1)
    preference_score = round(preference_score, 1)
    count_score = round(count_score, 1)
    distance_score = round(distance_score, 1)
    total = validity_score + preference_score + count_score + distance_score
    total -= 5 * sum(1 for i in hotel_issues if i["level"] == "severe")
    total = max(0.0, round(total, 1))

    severe_count = sum(1 for i in issues if i["level"] == "severe")
    result = {
        "city": city or None,
        "ok": severe_count == 0,
        "score": total,
        "score_breakdown": {
            "validity": validity_score,
            "preference": preference_score,
            "count": count_score,
            "distance": distance_score,
            "max": {"validity": SCORE_VALIDITY, "preference": SCORE_PREFERENCE,
                    "count": SCORE_COUNT, "distance": SCORE_DISTANCE},
        },
        "spot_count": len(names),
        "preference_hits": main_hits + secondary_hits,
        "preference_detail": {
            "main_hits": main_hits,
            "secondary_hits": secondary_hits,
            "coverage": round(coverage, 2),
        },
        "distance_note": "球面距离仅作参考，不等于路网通勤耗时；实际请以导航路线为准",
        "distance_jumps": [{"from": a, "to": b, "km": round(d, 1)} for a, b, d in jumps + severe_jumps],
        "issues": issues,             # 结构化：供模型判断优先级
        "issues_text": [i["message"] for i in issues],  # 通俗文本：供模型直接转述
        "suggestions": [i["message"] for i in issues if i["level"] == "warn"][:5],
        "hotel_issues": hotel_issues,
        "summary": {
            "preference": {"main_hits": main_hits, "secondary_hits": secondary_hits,
                           "coverage": round(coverage, 2), "total": len(names)},
            "problem_spots": sorted({i["target"] for i in issues if i["code"].startswith("spot_")}),
            "hotel_problems": sorted({i["target"] for i in hotel_issues}),
            "severe_count": severe_count,
            "warn_count": sum(1 for i in issues if i["level"] == "warn"),
        },
    }
    _log("critique_route", trace_id, city=city or None, spot_names=names, days=days, per_day=per_day,
         main_preferences=main_prefs, secondary_preferences=secondary_prefs,
         hotel_budget=hotel_budget, hotel_tags=hotel_tags, hotel_max_radius=hotel_max_radius,
         score=total, breakdown=result["score_breakdown"], issues=issues,
         day_preferences_reserved=day_preferences or None)
    return result


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
                "facilities": h.facilities,
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


# 供模型使用的工具声明（JSON Schema）
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_spots",
            "description": "查询某城市的真实景点数据。偏好只决定排序优先级（主偏好优先），保留少量备选，不做硬过滤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，例如 广州"},
                    "keyword": {"type": "string", "description": "关键词，如 山、博物馆，可空"},
                    "preferences": {"type": "array", "items": {"type": "string"},
                                    "description": "兼容旧参数，等同主偏好"},
                    "main_preferences": {"type": "array", "items": {"type": "string"},
                                         "description": "主偏好（权重更高）"},
                    "secondary_preferences": {"type": "array", "items": {"type": "string"},
                                              "description": "次要偏好"},
                    "day_preferences": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "逐日偏好（预留，当前版本不生效）",
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
            "description": "按城市与天数生成完整旅行路线（确定性算法），返回景点顺序、每天分组、总里程与提示。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_city": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "maximum": 10},
                    "per_day": {"type": "integer", "minimum": 1, "maximum": 4},
                    "preferences": {"type": "array", "items": {"type": "string"}},
                    "travel_type": {"type": "string",
                                    "enum": ["单人出行", "情侣出行", "家庭亲子", "老年休闲"]},
                    "start_location": {"type": "string"},
                    "day_preferences": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "逐日偏好（预留，当前版本不生效）",
                    },
                },
                "required": ["target_city", "days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "critique_route",
            "description": "路线自检（只读）：真实性40 + 偏好覆盖35（主偏好权重更高）+ 数量15 + 距离10（>=30km提醒，>=60km严重），并校验酒店预算/标签/半径；返回分项得分、结构化 issues、通俗 issues_text 与 summary。",
            "parameters": {
                "type": "object",
                "properties": {
                    "spot_names": {"type": "array", "items": {"type": "string"}},
                    "city": {"type": "string"},
                    "preferences": {"type": "array", "items": {"type": "string"}},
                    "main_preferences": {"type": "array", "items": {"type": "string"}},
                    "secondary_preferences": {"type": "array", "items": {"type": "string"}},
                    "days": {"type": "integer"},
                    "per_day": {"type": "integer"},
                    "hotel_list": {"type": "array", "items": {"type": "object"},
                                   "description": "search_hotels 返回的酒店对象（name/price_per_day/distance_km）"},
                    "hotel_budget": {"type": "number"},
                    "hotel_tags": {"type": "array", "items": {"type": "string"},
                                   "description": "酒店设施要求，如 早餐、民宿"},
                    "hotel_max_radius": {"type": "number"},
                    "day_preferences": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "逐日偏好（预留，当前版本不生效）",
                    },
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
                    "max_price": {"type": "number"},
                    "near_spot": {"type": "string"},
                    "radius_km": {"type": "number"},
                },
                "required": ["city"],
            },
        },
    },
]

TOOL_NAMES = {"search_spots", "make_route", "search_hotels", "critique_route"}


def execute_tool(name: str, args: dict, db: Session,
                 trace_id: Optional[str] = None) -> dict:
    """白名单分发；任何工具异常都转成 {"error": ...} 让模型自己纠错。

    返回 degraded=True 表示该工具单独降级，其它工具与结果不受影响。
    """
    if name not in TOOL_NAMES:
        return {"error": "未知工具：%s" % name, "degraded": True}
    args = dict(args or {})
    if name in ("make_route", "critique_route"):
        args.setdefault("trace_id", trace_id)
    try:
        if name == "search_spots":
            return tool_search_spots(db, **args)
        if name == "make_route":
            return tool_make_route(db, **args)
        if name == "critique_route":
            return tool_critique_route(db, **args)
        return tool_search_hotels(db, **args)
    except TypeError as exc:
        return {"error": "参数不合法：%s" % exc, "degraded": True}
    except ValueError as exc:
        return {"error": str(exc), "degraded": True}
    except Exception as exc:  # 工具失败不能中断整个 Agent
        return {"error": "工具执行失败：%s" % exc, "degraded": True}
