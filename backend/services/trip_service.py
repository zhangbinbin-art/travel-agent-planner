import heapq
import json
from hashlib import md5
from math import hypot, inf
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from core.pricing import get_ticket_price
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


def get_distance(spot_a: Spot, spot_b: Spot) -> float:
    """模拟距离（1 坐标单位≈1km），预留替换为真实地理距离(Haversine)的接口。

    当前项目没有真实经纬度数据，先用确定性的模拟坐标计算欧氏距离。
    后续若接入真实经纬度，只需要替换本函数实现，图的构建、Dijkstra、
    路线生成等上层逻辑都不用改动。
    """
    ax, ay = get_spot_point(spot_a)
    bx, by = get_spot_point(spot_b)
    return round(hypot(ax - bx, ay - by), 2)


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


def compute_budget(route: List, days: int) -> dict:
    """按路线顺序估算门票预算。

    路线元素可以是 RouteSpot 模型，也可以是保存到 route_json 后的字典。
    门票单价按景点名称从 core.pricing 读取，未知名称使用默认价格。
    返回 TripBudget 字段：days / items / ticket_total / daily_average。
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
    daily_average = round(ticket_total / safe_days, 2)
    return {
        "days": safe_days,
        "items": items,
        "ticket_total": ticket_total,
        "daily_average": daily_average,
    }


def generate_route(db: Session, spot_ids: List[int], start_spot_id: int, days: int = 1) -> dict:
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

    if len(ordered_ids) < 2:
        raise ValueError("至少选择两个景点")

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
        route.append(
            RouteSpot(
                id=spot.id,
                name=spot.name,
                city=spot.city,
                score=spot.score or 0,
                x=x,
                y=y,
                order=order,
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
    return {
        "spot_ids": walk_order,
        "route": route,
        "legs": legs,
        "total_distance": total_distance,
        "start_spot_id": start,
        "days": safe_days,
        "budget": compute_budget(route, safe_days),
    }


def save_trip(db: Session, user_id: int, name: str, spot_ids: List[int], start_spot_id: int, days: int = 1) -> Trip:
    """保存路线：始终服务端重算，绝不信任客户端传来的路线结果。"""
    result = generate_route(db, spot_ids, start_spot_id, days)

    payload = {
        "spot_ids": result["spot_ids"],
        "start_spot_id": result["start_spot_id"],
        "route": [item.model_dump() for item in result["route"]],
        "legs": [leg.model_dump() for leg in result["legs"]],
        "days": result["days"],
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
        budget = route_data.get("budget") or compute_budget(route, days)
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
    budget = route_data.get("budget") or compute_budget(route, days)
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
