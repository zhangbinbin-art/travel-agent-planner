import heapq
import json
import re
import urllib.parse
import urllib.request
from hashlib import md5
from math import hypot, inf
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from core.config import settings
from core.pricing import DEFAULT_HOTEL_PER_DAY, TRAFFIC_PRICE_PER_KM, get_ticket_price
from models import Spot, Trip
from schemas.trip import RouteLeg, RouteSpot

# 空路线结构：route_json 解析失败或为空时使用，保证上层拿到的永远是完整字典
_EMPTY_ROUTE = {
    "spot_ids": [],
    "start_spot_id": None,
    "route": [],
    "legs": [],
}


# ---------------------------------------------------------------------------
# 坐标与距离
# ---------------------------------------------------------------------------

def _city_anchor(city: str) -> Tuple[float, float]:
    """根据城市名生成稳定的基准坐标。

    注意：不能用 Python 内置 hash()，因为它对字符串按进程随机化，重启后坐标会变；
    这里使用 md5 摘要保证同一城市在任何进程/任何机器上都得到相同坐标。
    """
    digest = md5((city or "unknown").encode("utf-8")).digest()
    x = 100 + digest[0] * 2.4
    y = 100 + digest[1] * 2.0
    return (x, y)


def get_spot_point(spot: Spot) -> Tuple[float, float]:
    """由城市基准坐标 + 景点 id 的确定性偏移，得到景点的“模拟经纬度”坐标。

    坐标同时用于两点距离计算和前端 ECharts 散点图绘制，因此必须是确定性的。
    返回的坐标大致落在 [100, 700] x [100, 600] 的画布范围内。
    """
    base_x, base_y = _city_anchor(spot.city)
    dx = (spot.id * 37) % 61 - 30
    dy = (spot.id * 53) % 61 - 30
    return (round(base_x + dx, 2), round(base_y + dy, 2))


def get_spot_lnglat(spot: Spot) -> Tuple[Optional[float], Optional[float]]:
    """返回景点的真实经纬度 (lng, lat)，仅用于前端高德地图可视化。

    优先使用 spots 表里的真实坐标；表格中部分演示景点没有坐标，
    此时用城市真实中心坐标 + 由景点 id 决定的确定性小偏移近似（幅度约 2km），
    保证地图能落点且每次生成结果一致。
    该函数不参与距离与预算计算，距离仍由 get_distance 决定。
    """
    if spot.lng is not None and spot.lat is not None:
        return (float(spot.lng), float(spot.lat))
    center = _CITY_COORDS.get((spot.city or "").strip())
    if center is None:
        return (None, None)
    center_lat, center_lng = center
    # 用 md5(景点 id) 生成确定性抖动，幅度约 ±0.03/±0.025 度（约 ±3km），避免同城景点完全重合
    digest = md5(("lnglat-%s" % spot.id).encode("utf-8")).digest()
    d_lng = (digest[0] / 255.0 - 0.5) * 0.06
    d_lat = (digest[1] / 255.0 - 0.5) * 0.05
    return (round(center_lng + d_lng, 6), round(center_lat + d_lat, 6))


def _mock_distance(spot_a: Spot, spot_b: Spot) -> float:
    """模拟距离（1 坐标单位≈1km），保留 v0.8 的确定性算法。

    当前项目有可能没有真实经纬度数据，先用确定性的模拟坐标计算欧氏距离。
    这是无密钥/无网络时的安全兜底，计算结果与 v0.7/v0.8 完全一致。
    """
    ax, ay = get_spot_point(spot_a)
    bx, by = get_spot_point(spot_b)
    return round(hypot(ax - bx, ay - by), 2)


# 高德距离结果的内存缓存：key 为排序后的景点 id 元组，值为最终采用的公里数。
# 缓存真实距离和模拟距离，避免重复调用高德接口，把每日额度消耗降到最低；
# 查询失败时也会缓存兜底结果，使本次进程后续请求直接走模拟距离而不反复重试。
_AMAP_CACHE: dict = {}


def clear_distance_cache() -> None:
    """清空距离缓存（测试或运行期手动刷新时使用）。"""
    _AMAP_CACHE.clear()


def _fetch_amap_distance(origin: Tuple[float, float], dest: Tuple[float, float]) -> Optional[float]:
    """调用高德驾车距离矩阵，返回公里数；任何异常/非 1 状态/空结果都返回 None。

    仅使用标准库 urllib，不引入额外依赖。参数 origin/dest 均为 (lng, lat)，
    与高德接口要求的“经度在前、纬度在后”保持一致。
    """
    try:
        if not settings.AMAP_KEY:
            return None
        params = urllib.parse.urlencode(
            {
                "origins": f"{origin[0]},{origin[1]}",
                "destination": f"{dest[0]},{dest[1]}",
                "type": 1,  # 1 表示驾车距离
                "key": settings.AMAP_KEY,
            }
        )
        url = "https://restapi.amap.com/v3/distance?" + params
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("status") != "1":
            return None
        results = data.get("results") or []
        if not results:
            return None
        raw = results[0].get("distance")
        if raw in (None, ""):
            return None
        meters = float(raw)
        if meters <= 0:
            return None
        return round(meters / 1000, 2)
    except Exception:
        # 网络超时、DNS 失败、返回非 JSON、字段结构异常等一律降级，绝不向上抛出
        return None


def get_distance(spot_a: Spot, spot_b: Spot) -> float:
    """返回两景点间距离（公里），优先真实驾车距离，失败时自动降级为模拟距离。

    答辩时可自由切换真实距离/模拟距离——在 backend/.env 配 AMAP_KEY 即为真实距离，
    留空即自动走原有 md5 模拟距离，没有任何密钥或额度风险；上层构图与 Dijkstra
    完全不感知数据源，只消费本函数返回的公里数。
    """
    # 两个景点都有 id 时才可缓存；用排序后的元组保证 (a,b) 与 (b,a) 命中同一缓存
    key = None
    if spot_a.id is not None and spot_b.id is not None:
        key = tuple(sorted((spot_a.id, spot_b.id)))
        if key in _AMAP_CACHE:
            return _AMAP_CACHE[key]

    distance = None
    # 扩展方案：配置AMAP_KEY后可切换高德真实驾车距离矩阵，受接口配额限制，毕设暂不启用
    # 只有配置了密钥且两个景点都有真实经纬度时才尝试调用高德
    if (
        settings.AMAP_KEY
        and spot_a.lat is not None
        and spot_a.lng is not None
        and spot_b.lat is not None
        and spot_b.lng is not None
    ):
        try:
            candidate = _fetch_amap_distance(
                (spot_a.lng, spot_a.lat),
                (spot_b.lng, spot_b.lat),
            )
        except Exception:
            # 距离源是可选增强，任何异常都必须降级为模拟距离，绝不影响路线生成
            candidate = None
        if candidate is not None and candidate > 0:
            distance = candidate

    if distance is None:
        distance = _mock_distance(spot_a, spot_b)

    if key is not None:
        _AMAP_CACHE[key] = distance
    return distance


# ---------------------------------------------------------------------------
# 图与手写 Dijkstra
# ---------------------------------------------------------------------------

def build_graph(spots: List[Spot]) -> dict:
    """构建景点完全无向图：{spot_id: {other_spot_id: distance}}。

    任意两个景点之间都有一条边，边权由 get_distance 计算。
    """
    graph = {spot.id: {} for spot in spots}
    for i in range(len(spots)):
        for j in range(i + 1, len(spots)):
            a, b = spots[i], spots[j]
            distance = get_distance(a, b)
            # 无向图：两个方向都要存
            graph[a.id][b.id] = distance
            graph[b.id][a.id] = distance
    return graph


def dijkstra(graph: dict, start: int, target: Optional[int] = None) -> Tuple[dict, dict]:
    """手写 Dijkstra 单源最短路算法（不依赖 networkx / scipy / igraph）。

    参数：
        graph: 邻接字典 {node: {neighbor: weight}}
        start: 起点
        target: 可选终点；一旦弹出目标节点即可提前结束（只求单点最短路时更快）

    返回：
        (dist, prev)
        dist[node] = 从 start 到 node 的最短距离；不可达节点保持 inf
        prev[node] = 最短路上的前驱节点，用于回溯路径

    算法说明（论文可引用）：
        1. 初始化：起点距离为 0，其余节点距离为无穷大；
        2. 使用最小堆（优先队列）每次取出当前距离最小的未确定节点 u；
        3. 以 u 为中转点松弛它的所有邻居 v：
               if dist[u] + w(u, v) < dist[v]: 更新 dist[v] 和 prev[v]
        4. 堆中可能有同一节点的多个过期距离，若取出的距离大于 dist[u] 则说明是
           旧记录，直接跳过（lazy deletion）；
        5. 所有节点处理完（或目标节点被弹出）后，dist 即为最短距离。
    """
    # 初始化距离表与前驱表
    dist = {node: inf for node in graph}
    prev = {node: None for node in graph}

    if start not in graph:
        # 起点不在图中：直接返回全无穷大，调用方可据此判断不可达
        return dist, prev

    dist[start] = 0
    # 最小堆元素为 (当前累计距离, 节点 id)
    heap = [(0, start)]

    while heap:
        current_dist, u = heapq.heappop(heap)

        # 过期堆记录：之前已经找到过更短的路径，跳过
        if current_dist > dist[u]:
            continue

        # 只求 start -> target 时可提前结束
        if target is not None and u == target:
            break

        # 松弛所有邻居
        for v, weight in graph.get(u, {}).items():
            new_dist = current_dist + weight
            if new_dist < dist[v]:
                dist[v] = new_dist
                prev[v] = u
                heapq.heappush(heap, (new_dist, v))

    return dist, prev


def shortest_path(graph: dict, start: int, end: int) -> Tuple[List[int], float]:
    """返回 start -> end 的最短路节点序列与距离。

    不可达时返回 ([], inf)。路径通过 dijkstra 的 prev 表反向回溯得到。
    """
    dist, prev = dijkstra(graph, start, target=end)
    if start not in dist or end not in dist or dist[end] == inf:
        return [], inf

    # 从终点沿 prev 回溯到起点
    path = []
    node = end
    while node is not None:
        path.append(node)
        if node == start:
            break
        node = prev.get(node)
    else:
        # 回溯不到起点，说明确实不可达（正常情况下不会发生）
        return [], inf

    path.reverse()
    return path, dist[end]


# ---------------------------------------------------------------------------
# 路线生成与持久化
# ---------------------------------------------------------------------------

def _dedupe_keep_order(values: List[int]) -> List[int]:
    """按原始顺序去重。"""
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def compute_budget(route: List, days: int, total_distance=0.0, hotel_per_day=None) -> dict:
    """按路线顺序估算三类预算：门票、食宿、交通。

    路线元素可以是 RouteSpot 模型，也可以是保存到 route_json 后的字典。
    - 门票：按景点名称从 core.pricing 读取单价，未知名称使用默认价格；
    - 食宿：天数 * 每日食宿单价（未传时使用 DEFAULT_HOTEL_PER_DAY）；
    - 交通：总里程 * 每公里交通单价（TRAFFIC_PRICE_PER_KM，仅后端配置）。
    返回 TripBudget 全部字段，其中 daily_average 保留 v0.8 的“门票日均”语义。
    """
    safe_days = days if days and days >= 1 else 1
    items = []
    for entry in route or []:
        if isinstance(entry, dict):
            spot_id = entry.get("id")
            name = entry.get("name")
        else:
            spot_id = getattr(entry, "id", None)
            name = getattr(entry, "name", None)
        items.append(
            {
                "spot_id": spot_id,
                "name": name or "",
                "ticket_price": get_ticket_price(name),
            }
        )

    ticket_total = round(sum(item["ticket_price"] for item in items), 2)
    safe_hotel = DEFAULT_HOTEL_PER_DAY if hotel_per_day is None else float(hotel_per_day)
    hotel_total = round(safe_days * safe_hotel, 2)
    traffic_total = round(float(total_distance or 0) * TRAFFIC_PRICE_PER_KM, 2)
    grand_total = round(ticket_total + hotel_total + traffic_total, 2)
    daily_avg = round(grand_total / safe_days, 2)
    # v0.8 语义：daily_average 仍表示“门票日均”，保留给旧前端使用
    daily_average = round(ticket_total / safe_days, 2)
    return {
        "days": safe_days,
        "items": items,
        "ticket_total": ticket_total,
        "hotel_total": hotel_total,
        "traffic_total": traffic_total,
        "grand_total": grand_total,
        "daily_avg": daily_avg,
        "daily_average": daily_average,
    }


def generate_route(
    db: Session,
    spot_ids: List[int],
    start_spot_id: int,
    days: int = 1,
    hotel_per_day=None,
) -> dict:
    """根据用户选择的景点生成一条游览路线。

    思路：
        1. 去重并校验景点是否都存在；
        2. 起点若不在选择列表中，则插入到列表首位；
        3. 构建完全无向图；
        4. 贪心最近邻（每一步用 Dijkstra 求当前点到各未访问点的最短路距离，
           选择最近的一个）得到访问顺序；
        5. 相邻访问点之间再用 shortest_path 展开，把中转节点补进真实步行顺序；
        6. 生成每段 legs 与总距离。
    """
    # 1. 去重（保持用户选择顺序）
    unique_ids = _dedupe_keep_order(spot_ids)

    # 2. 一次性加载景点（起点不在选择列表时也要一起加载），记录缺失 id
    query_ids = list(unique_ids)
    if start_spot_id not in query_ids:
        query_ids.append(start_spot_id)
    spots = db.query(Spot).filter(Spot.id.in_(query_ids)).all() if query_ids else []
    spot_map = {spot.id: spot for spot in spots}
    missing = sorted(set(unique_ids) - set(spot_map))
    if missing:
        raise ValueError(f"景点不存在: {missing}")

    # 3. 起点不在列表中时插入首位
    ordered_ids = list(unique_ids)
    if start_spot_id not in ordered_ids:
        ordered_ids.insert(0, start_spot_id)

    if len(ordered_ids) < 1:
        raise ValueError("至少选择一个景点")

    # 起点本身也必须存在（覆盖“起点不在 spot_ids 里且 id 非法”的情况）
    if start_spot_id not in spot_map:
        raise ValueError(f"景点不存在: {[start_spot_id]}")

    # 4. 构建完全图并做贪心最近邻
    selected_spots = [spot_map[spot_id] for spot_id in ordered_ids]
    graph = build_graph(selected_spots)

    start = start_spot_id
    greedy_order = [start]
    unvisited = set(ordered_ids)
    unvisited.discard(start)
    current = start

    while unvisited:
        # 用 Dijkstra 求当前点到所有节点的最短路距离，再挑最近的未访问点
        distances, _ = dijkstra(graph, current)
        next_id = min(unvisited, key=lambda node: (distances.get(node, inf), node))
        greedy_order.append(next_id)
        unvisited.remove(next_id)
        current = next_id

    # 5. 展开相邻访问点之间的最短路，拼接真实步行顺序（去掉重复的衔接节点）
    walk_order: List[int] = []
    for from_id, to_id in zip(greedy_order, greedy_order[1:]):
        path, _ = shortest_path(graph, from_id, to_id)
        if not path:
            # 完全图正常不会不可达；保底跳过，避免生成断裂路线
            continue
        if not walk_order:
            walk_order.extend(path)
        else:
            walk_order.extend(path[1:])

    # 若只有一个点（理论上已被上面的长度校验拦住），至少保留起点
    if not walk_order:
        walk_order = [start]

    # 6. 生成 RouteSpot / RouteLeg / 总距离
    route: List[RouteSpot] = []
    for order, spot_id in enumerate(walk_order):
        spot = spot_map[spot_id]
        x, y = get_spot_point(spot)
        lng, lat = get_spot_lnglat(spot)
        route.append(
            RouteSpot(
                id=spot.id,
                name=spot.name,
                city=spot.city,
                score=spot.score or 0,
                x=x,
                y=y,
                order=order,
                lng=lng,
                lat=lat,
            )
        )

    legs: List[RouteLeg] = []
    for from_id, to_id in zip(walk_order, walk_order[1:]):
        legs.append(
            RouteLeg(
                from_spot_id=from_id,
                to_spot_id=to_id,
                distance=get_distance(spot_map[from_id], spot_map[to_id]),
            )
        )

    total_distance = round(sum(leg.distance for leg in legs), 2)

    safe_days = days if days and days >= 1 else 1
    # 解析每日食宿单价，未传时使用 pricing 中的默认值，便于保存时一并持久化
    safe_hotel_value = DEFAULT_HOTEL_PER_DAY if hotel_per_day is None else float(hotel_per_day)
    budget = compute_budget(route, safe_days, total_distance, hotel_per_day)
    return {
        "spot_ids": walk_order,
        "route": route,
        "legs": legs,
        "total_distance": total_distance,
        "start_spot_id": start,
        "days": safe_days,
        "hotel_per_day": safe_hotel_value,
        "budget": budget,
    }


def save_trip(
    db: Session,
    user_id: int,
    name: str,
    spot_ids: List[int],
    start_spot_id: int,
    days: int = 1,
    hotel_per_day=None,
) -> Trip:
    """保存路线：始终服务端重算，绝不信任客户端传来的路线结果。"""
    result = generate_route(db, spot_ids, start_spot_id, days, hotel_per_day)

    payload = {
        "spot_ids": result["spot_ids"],
        "start_spot_id": result["start_spot_id"],
        "route": [item.model_dump() for item in result["route"]],
        "legs": [leg.model_dump() for leg in result["legs"]],
        "days": result["days"],
        "hotel_per_day": result["hotel_per_day"],
        "budget": result["budget"],
    }

    trip = Trip(
        user_id=user_id,
        name=name,
        route_json=json.dumps(payload, ensure_ascii=False),
        total_distance=result["total_distance"],
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def parse_route(trip: Trip) -> dict:
    """解析 trips.route_json；只捕获 JSONDecodeError，返回完整空结构。"""
    if not trip or not trip.route_json:
        return dict(_EMPTY_ROUTE)

    try:
        data = json.loads(trip.route_json)
    except json.JSONDecodeError:
        return dict(_EMPTY_ROUTE)

    if not isinstance(data, dict):
        return dict(_EMPTY_ROUTE)

    # 用默认结构兜底，保证 route / legs / start_spot_id 等键始终存在
    result = dict(_EMPTY_ROUTE)
    result.update(data)
    return result


# v0.9 新增的预算字段：旧路线（v0.8）的 stored budget 缺少这些字段
_BUDGET_V09_FIELDS = ("hotel_total", "traffic_total", "grand_total", "daily_avg")


def _resolve_budget(route_data: dict, route: List, days: int, total_distance) -> dict:
    """优先复用已保存的预算，存量旧路线则重新计算完整预算。

    已保存的 v0.9 预算直接返回（保持原值，不重算）；若 stored budget 缺少任一
    v0.9 字段（v0.8 存量数据），则按当前配置重新计算，保证响应模型校验通过。
    """
    stored = route_data.get("budget")
    if isinstance(stored, dict) and all(field in stored for field in _BUDGET_V09_FIELDS):
        return stored
    return compute_budget(route, days, total_distance or 0, route_data.get("hotel_per_day"))


def get_my_trips(db: Session, user_id: int, page: int, page_size: int) -> dict:
    """分页返回当前用户的路线列表，按创建时间倒序（同一时间按 id 倒序）。"""
    query = db.query(Trip).filter(Trip.user_id == user_id)
    total = query.count()
    trips = (
        query.order_by(Trip.created_at.desc(), Trip.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for trip in trips:
        route_data = parse_route(trip)
        route = route_data.get("route") or []
        days = route_data.get("days") or 1
        budget = _resolve_budget(route_data, route, days, trip.total_distance)
        items.append(
            {
                "id": trip.id,
                "name": trip.name,
                "total_distance": trip.total_distance or 0,
                "spot_count": len(route),
                "created_at": trip.created_at,
                "days": days,
                "budget": budget,
            }
        )

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_trip_by_id(db: Session, trip_id: int) -> Optional[Trip]:
    return db.query(Trip).filter(Trip.id == trip_id).first()


def delete_trip(db: Session, trip: Trip) -> Trip:
    db.delete(trip)
    db.commit()
    return trip


def build_detail(trip: Trip) -> dict:
    """把 Trip ORM 对象组装成 TripDetail 形状的字典。"""
    route_data = parse_route(trip)
    route = route_data.get("route") or []
    days = route_data.get("days") or 1
    budget = _resolve_budget(route_data, route, days, trip.total_distance)
    return {
        "id": trip.id,
        "name": trip.name,
        "total_distance": trip.total_distance or 0,
        "spot_count": len(route),
        "created_at": trip.created_at,
        "user_id": trip.user_id,
        "route": route,
        "legs": route_data.get("legs") or [],
        "start_spot_id": route_data.get("start_spot_id"),
        "days": days,
        "budget": budget,
    }

# ---------------------------------------------------------------------------
# v0.10 纯智能规划：偏好加权推荐（规则引擎，不接大模型）
# ---------------------------------------------------------------------------

from models import Hotel  # noqa: E402

_PREF_THEME = {
    "自然风光": "自然风景",
    "人文古迹": "历史古迹",
    "游乐乐园": "主题乐园",
    "城市逛街": "城市观光",
}

_PREF_KEYWORDS = {
    "美食探店": ("美食", "小吃", "探店", "夜市", "餐厅"),
    "徒步登山": ("徒步", "登山", "山", "森林", "步道"),
    "海滨海岛": ("海", "海滨", "海岛", "沙滩", "海岸"),
    "亲子出游": ("亲子", "乐园", "动物园", "儿童", "海洋王国"),
}


def _hotel_type(name: str) -> str:
    name = name or ""
    if "民宿" in name:
        return "民宿"
    if "电竞" in name:
        return "电竞酒店"
    if "星期八" in name:
        return "连锁酒店"
    if "西瓜" in name:
        return "商务酒店"
    return "其他酒店"


def _spot_text(spot) -> str:
    return " ".join(
        [str(getattr(spot, "name", "") or ""), str(getattr(spot, "tags", "") or ""), str(getattr(spot, "description", "") or "")]
    )


def _matches_preference(spot, pref: str) -> bool:
    theme = getattr(spot, "theme", None) or ""
    text = _spot_text(spot)
    if pref in _PREF_THEME:
        target = _PREF_THEME[pref]
        return theme == target or target in text
    for keyword in _PREF_KEYWORDS.get(pref, ()):
        if keyword in text:
            return True
    return False


def score_spot(spot, travel_type: str, preferences) -> float:
    """规则加权引擎：base_score + 出行类型加权 + 偏好加权。"""
    score = float(getattr(spot, "score", 0) or 0)
    theme = getattr(spot, "theme", None) or ""
    text = _spot_text(spot)

    if travel_type == "家庭亲子":
        if theme == "主题乐园":
            score += 3
        if "徒步" in text or "登山" in text:
            score -= 2
    elif travel_type == "老年休闲":
        if "徒步" in text or "登山" in text:
            score -= 3
        if theme == "历史古迹":
            score += 2
    elif travel_type == "单人出行":
        if "美食" in text or "小吃" in text:
            score += 2
        if "徒步" in text or "登山" in text:
            score += 1
    elif travel_type == "情侣出行":
        if theme == "自然风景":
            score += 2

    for pref in set(preferences or []):
        if _matches_preference(spot, pref):
            score += 2
    return round(score, 2)


def _departure_distance(lat, lng, spot) -> Optional[float]:
    """出发点到景点的距离；无密钥或坐标时返回 None（排序回退到评分顺序）。"""
    if lat is None or lng is None:
        return None
    if not (settings.AMAP_KEY and spot.lat is not None and spot.lng is not None):
        return None
    try:
        return _fetch_amap_distance((lng, lat), (spot.lng, spot.lat))
    except Exception:
        return None


def _order_day(group, start_spot):
    """贪心最近邻排序，减少折返；day1 可从离出发位置最近的景点开始。"""
    remaining = [spot for spot in group]
    if not remaining:
        return []
    order = []
    current = start_spot if start_spot in remaining else remaining[0]
    remaining.remove(current)
    order.append(current)
    while remaining:
        next_spot = min(remaining, key=lambda s: (get_distance(current, s), s.id))
        remaining.remove(next_spot)
        order.append(next_spot)
        current = next_spot
    return order


def _pref_hit(spot, preferences) -> int:
    """是否命中任一游玩偏好（1/0）。"""
    for pref in set(preferences or []):
        if _matches_preference(spot, pref):
            return 1
    return 0


def _order_day_weighted(group, start_spot, preferences):
    """偏好+距离加权贪心：score = 偏好分*0.6 + 归一化距离分*0.4。

    距离分在「当前剩余候选」中做 min-max 归一化，越近越接近 1；
    同分时按欧氏距离升序（更近优先）。
    """
    remaining = list(group)
    if not remaining:
        return []
    order = []
    current = start_spot if start_spot in remaining else remaining[0]
    remaining.remove(current)
    order.append(current)

    while remaining:
        distances = {s.id: get_distance(current, s) for s in remaining}
        lo, hi = min(distances.values()), max(distances.values())
        span = hi - lo

        def rank(spot):
            pref = _pref_hit(spot, preferences)
            dist = distances[spot.id]
            norm = 1.0 if span <= 1e-9 else (hi - dist) / span
            score = round(pref * 0.6 + norm * 0.4, 4)
            # 分数高优先；同分距离近优先；再按 id 稳定排序
            return (-score, dist, spot.id)

        next_spot = min(remaining, key=rank)
        remaining.remove(next_spot)
        order.append(next_spot)
        current = next_spot
    return order


def recommend_hotels(db: Session, payload) -> list:
    query = db.query(Hotel).filter(Hotel.status == "on_shelf")
    # 单目的地：优先按地址包含城市名匹配；匹配不到时按坐标距离兜底（≤100km）
    city_hotels = query.filter(Hotel.address.contains(payload.target_city)).all()
    if city_hotels:
        hotels = city_hotels
    else:
        center = _CITY_COORDS.get((payload.target_city or "").strip())
        hotels = []
        if center:
            for h in query.all():
                if h.lat is None or h.lng is None:
                    continue
                if _haversine_km(center[0], center[1], float(h.lat), float(h.lng)) <= 100:
                    hotels.append(h)
    if payload.min_price is not None:
        query = query.filter(Hotel.price_per_day >= payload.min_price)
    if payload.max_price is not None:
        query = query.filter(Hotel.price_per_day <= payload.max_price)
    if payload.min_env_score is not None:
        query = query.filter(Hotel.env_score >= payload.min_env_score)
    if payload.min_service_score is not None:
        query = query.filter(Hotel.service_score >= payload.min_service_score)
    # 注意：上面已在地址匹配阶段取过 hotels，这里只对 fallback 结果做二次过滤
    hotels = [
        h
        for h in hotels
        if (payload.min_price is None or (h.price_per_day or 0) >= payload.min_price)
        and (payload.max_price is None or (h.price_per_day or 0) <= payload.max_price)
        and (payload.min_env_score is None or (h.env_score or 0) >= payload.min_env_score)
        and (payload.min_service_score is None or (h.service_score or 0) >= payload.min_service_score)
    ]

    if payload.hotel_types:
        hotels = [h for h in hotels if _hotel_type(h.name) in payload.hotel_types]
    if payload.hotel_features:
        hotels = [
            h
            for h in hotels
            if all(f in (h.facilities or "") for f in payload.hotel_features)
        ]

    hotels.sort(key=lambda h: ((h.env_score or 0) + (h.service_score or 0)), reverse=True)
    return [
        {
            "id": h.id,
            "name": h.name,
            "address": h.address,
            "price_per_day": h.price_per_day,
            "cover_img": h.cover_img,
            "description": h.description,
            "facilities": h.facilities,
            "env_score": h.env_score,
            "service_score": h.service_score,
            # 仅用于行程地图打点，不参与距离矩阵 / 路径排序
            "lng": h.lng,
            "lat": h.lat,
            "hotel_type": _hotel_type(h.name),
            "status": h.status,
        }
        for h in hotels[:6]
    ]


def smart_recommend(db: Session, payload) -> dict:
    """单目的地智能推荐：评分排序 -> 按天拆分(每日≤3) -> 就近排序 -> 预算与酒店。"""
    spots = db.query(Spot).filter(Spot.city == payload.target_city).all()
    if not spots:
        raise ValueError(f"目标城市暂无可推荐景点: {payload.target_city}")

    scored = [(score_spot(s, payload.travel_type, payload.preferences), s) for s in spots]
    scored.sort(key=lambda item: (-item[0], -(float(getattr(item[1], "score", 0) or 0)), item[1].id))

    safe_days = max(1, min(int(payload.days or 1), 10))
    # 每日景点数量：1~4，越界钳位
    safe_per_day = max(1, min(int(getattr(payload, "per_day", 3) or 3), 4))
    need = safe_days * safe_per_day
    total_spots = len(spots)
    # 资源不足时自动降级：需求数钳到实际可用景点数，不报错、也不复用同一景点
    degraded = total_spots < need
    effective_need = min(need, total_spots)
    if degraded:
        print(
            "[smart_recommend] 景点资源不足，自动降级：需求=%d 实际可用=%d 城市=%s"
            % (need, total_spots, payload.target_city)
        )

    # ① 偏好优先池：命中任一偏好的景点
    preferred = [s for _, s in scored if _pref_hit(s, payload.preferences) == 1]
    # ② 其余景点作为补充池
    rest = [s for _, s in scored if _pref_hit(s, payload.preferences) == 0]

    if len(preferred) >= effective_need:
        spot_pool = preferred[:effective_need]
        extra_count = 0
    else:
        spot_pool = preferred + rest[: effective_need - len(preferred)]
        extra_count = effective_need - len(preferred)

    print(
        "[smart_recommend] 城市=%s 天数=%d 每日=%d 需求=%d 可用=%d 优先池=%d 补充=%d 候选=%d"
        % (
            payload.target_city,
            safe_days,
            safe_per_day,
            need,
            total_spots,
            len(preferred),
            extra_count,
            len(spot_pool),
        )
    )
    if not spot_pool:
        raise ValueError("没有符合偏好的景点")

    # 景点按天均分：每天尽量平均，优先保证每天至少 1 个；不足时复用最高分景点
    reused = False
    allocations = []
    if len(spot_pool) >= safe_days:
        base, rem = divmod(len(spot_pool), safe_days)
        cursor = 0
        for day_idx in range(safe_days):
            count = base + (1 if day_idx < rem else 0)
            allocations.append(spot_pool[cursor : cursor + count])
            cursor += count
    else:
        # 景点不足以覆盖每一天时：一天一个，剩余天数留空（不复用同一景点）
        for day_idx in range(safe_days):
            if day_idx < len(spot_pool):
                allocations.append([spot_pool[day_idx]])
            else:
                allocations.append([])

    ordered_route = []
    day_plans = []
    seen_spot_ids = set()
    for idx, group in enumerate(allocations):
        if not group:
            continue
        start_spot = group[0]
        if idx == 0:
            # 第一天从离出发位置最近的景点开始
            best = None
            best_dist = None
            for spot in group:
                dist = _departure_distance(payload.start_lat, payload.start_lng, spot)
                if dist is not None and (best_dist is None or dist < best_dist):
                    best, best_dist = spot, dist
            if best is not None:
                start_spot = best
        day_order = _order_day_weighted(group, start_spot, payload.preferences)
        print(
            "[smart_recommend] 第%d天顺序: %s"
            % (idx + 1, " -> ".join("%s(偏好%s)" % (s.name, _pref_hit(s, payload.preferences)) for s in day_order))
        )
        # route 只保留唯一景点（复用景点不重复计入路线与预算）
        for spot in day_order:
            if spot.id not in seen_spot_ids:
                seen_spot_ids.add(spot.id)
                ordered_route.append(spot)
        day_plans.append(
            {
                "day": idx + 1,
                "spot_ids": [s.id for s in day_order],
                "spot_names": [s.name for s in day_order],
            }
        )

    route: List[RouteSpot] = []
    for order, spot in enumerate(ordered_route):
        x, y = get_spot_point(spot)
        lng, lat = get_spot_lnglat(spot)
        route.append(
            RouteSpot(
                id=spot.id,
                name=spot.name,
                city=spot.city,
                score=spot.score or 0,
                x=x,
                y=y,
                order=order,
                lng=lng,
                lat=lat,
            )
        )

    legs: List[RouteLeg] = []
    for a, b in zip(ordered_route, ordered_route[1:]):
        legs.append(RouteLeg(from_spot_id=a.id, to_spot_id=b.id, distance=get_distance(a, b)))
    total_distance = round(sum(leg.distance for leg in legs), 2)

    # 出发地 -> 第一个景点：作为整条路线起点距离并入总里程与交通预算
    departure_distance = _departure_leg_distance(payload, ordered_route[0]) if ordered_route else None
    if departure_distance:
        total_distance = round(total_distance + departure_distance, 2)

    # 自动推荐酒店：仅从满足筛选条件的同城酒店池中挑选 1 家（环境+服务总分最高）
    hotels = recommend_hotels(db, payload)

    # 距离过滤：离目标城市中心 > 40km 的酒店不参与推荐与地图打点
    city_center = _CITY_COORDS.get((payload.target_city or "").strip())
    if city_center is None:
        coord_spots = [s for s in spots if s.lat is not None and s.lng is not None]
        if coord_spots:
            city_center = (
                sum(float(s.lat) for s in coord_spots) / len(coord_spots),
                sum(float(s.lng) for s in coord_spots) / len(coord_spots),
            )
    if city_center:
        before_count = len(hotels)
        hotels = [
            h
            for h in hotels
            if h.get("lat") is not None
            and h.get("lng") is not None
            and _haversine_km(city_center[0], city_center[1], float(h["lat"]), float(h["lng"])) <= 40
        ]
        print(
            "[smart_recommend] 酒店距离过滤(<=40km)：%d -> %d 家"
            % (before_count, len(hotels))
        )
    auto_hotel = None
    if hotels:
        best = hotels[0]
        city = ""
        match = re.match(r"^(.+?市)", best.get("address") or "")
        if match:
            city = match.group(1).replace("市", "")
        auto_hotel = {
            "hotel_id": best.get("id"),
            "hotel_name": best.get("name"),
            "price": best.get("price_per_day"),
            "city": city or payload.target_city,
            # 兼容前端下拉回填使用的字段
            "id": best.get("id"),
            "name": best.get("name"),
            "price_per_day": best.get("price_per_day"),
            "address": best.get("address"),
            "env_score": best.get("env_score"),
            "service_score": best.get("service_score"),
            "facilities": best.get("facilities"),
            "cover_img": best.get("cover_img"),
            "description": best.get("description"),
            "status": best.get("status"),
        }

    # 预算：用户未手动指定时，使用自动推荐酒店的单价
    effective_hotel_price = payload.hotel_per_day
    if effective_hotel_price is None and auto_hotel is not None:
        effective_hotel_price = float(auto_hotel.get("price") or 0)
    budget = compute_budget(route, safe_days, total_distance, effective_hotel_price)

    # 节点组装：按天分组，先排当天全部景点，末尾只追加 1 次当天酒店
    route_map = {item.id: item for item in route}
    nodes = []
    for plan in day_plans:
        day_spots = [route_map[i] for i in plan["spot_ids"] if i in route_map]
        for spot in day_spots:
            nodes.append(
                {"node_type": "spot", "id": spot.id, "name": spot.name, "score": spot.score, "day": plan["day"]}
            )
        if auto_hotel is not None:
            nodes.append(
                {
                    "node_type": "hotel",
                    "id": auto_hotel["hotel_id"],
                    "name": auto_hotel["hotel_name"],
                    "score": None,
                    "day": plan["day"],
                }
            )

    daily_hotels = []
    if auto_hotel is not None:
        for plan in day_plans:
            daily_hotels.append(
                {
                    "day": plan["day"],
                    "hotel_id": auto_hotel["hotel_id"],
                    "hotel_name": auto_hotel["hotel_name"],
                    "price": auto_hotel["price"],
                    "city": auto_hotel["city"],
                }
            )

    # ------------------------------------------------------------------
    # 地图点位拆分（v0.14）
    #   route_list    : 只有景点，顺序与贪心/最近邻算法结果完全一致，用于连线
    #   hotel_markers : 只有酒店，仅打点展示，不送入距离矩阵、不参与路径排序
    # 说明：两者都只做可视化，里程与预算仍由后端 Haversine/模拟距离计算。
    # ------------------------------------------------------------------
    route_list = [
        {"id": item.id, "name": item.name, "lng": item.lng, "lat": item.lat, "type": "spot"}
        for item in route
        if item.lng is not None and item.lat is not None
    ]
    hotel_markers = []
    seen_hotel_ids = set()
    for hotel in hotels or []:
        hotel_id = hotel.get("id")
        lng = hotel.get("lng")
        lat = hotel.get("lat")
        if hotel_id in seen_hotel_ids or lng is None or lat is None:
            continue
        seen_hotel_ids.add(hotel_id)
        hotel_markers.append(
            {
                "id": hotel_id,
                "name": hotel.get("name"),
                "lng": float(lng),
                "lat": float(lat),
                "price": float(hotel.get("price_per_day") or 0),
                "env_score": hotel.get("env_score") or 0,
                "service_score": hotel.get("service_score") or 0,
                "cover": hotel.get("cover_img"),
                "description": hotel.get("description"),
                "address": hotel.get("address"),
                "type": "hotel",
            }
        )

    return {
        "route": route,
        "route_list": route_list,
        "hotel_markers": hotel_markers,
        "legs": legs,
        "total_distance": total_distance,
        "departure_distance": departure_distance,
        "budget": budget,
        "day_plans": day_plans,
        "recommended_hotels": hotels,
        "recommended_hotel": auto_hotel,
        "daily_hotels": daily_hotels,
        "no_hotel_match": auto_hotel is None,
        "spot_reused": reused,
        "matched_spot_count": len({s.id for s in spot_pool}),
        "nodes": nodes,
        "hotel_per_day": effective_hotel_price,
        "target_city": payload.target_city,
        "start_location": payload.start_location,
        "start_lat": payload.start_lat,
        "start_lng": payload.start_lng,
    }

# 常用城市坐标（用于无高德 Key 时估算 出发地 -> 目的地 距离）
_CITY_COORDS = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "杭州": (30.2741, 120.1551),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "南京": (32.0603, 118.7969),
    "苏州": (31.2989, 120.5853),
    "厦门": (24.4798, 118.0894),
    "桂林": (25.2736, 110.29),
    "珠海": (22.2707, 113.5767),
    "嘉兴": (30.7461, 120.7555),
    "佛山": (23.0218, 113.1219),
    "成都": (30.5728, 104.0668),
    "西安": (34.3416, 108.9398),
    "重庆": (29.563, 106.5516),
    "武汉": (30.5928, 114.3055),
    "长沙": (28.2282, 112.9388),
    "青岛": (36.0671, 120.3826),
    "天津": (39.3434, 117.3616),
    "昆明": (24.8801, 102.8329),
    "三亚": (18.2528, 109.5119),
}


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    from math import asin, cos, radians, sin, sqrt

    lat1, lng1, lat2, lng2 = map(float, (lat1, lng1, lat2, lng2))
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return round(2 * 6371 * asin(sqrt(a)), 2)


def _departure_leg_distance(payload, first_spot) -> Optional[float]:
    """出发地 -> 第一个景点距离：优先高德，缺失时用城市坐标 haversine 估算。"""
    if payload.start_lat is None or payload.start_lng is None:
        return None
    explicit = _departure_distance(payload.start_lat, payload.start_lng, first_spot)
    if explicit is not None:
        return explicit
    target = _CITY_COORDS.get((payload.target_city or "").strip())
    if not target:
        return None
    dist = _haversine_km(payload.start_lat, payload.start_lng, target[0], target[1])
    return dist if dist > 0.1 else 0.0
