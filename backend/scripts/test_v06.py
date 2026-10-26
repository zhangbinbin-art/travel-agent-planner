import os
import sys
from math import inf, isinf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt
from fastapi.testclient import TestClient

from core.config import settings
from core.database import SessionLocal
from main import app
from services.trip_service import shortest_path

c = TestClient(app)
created_trip_ids = []
passed = 0


def ok(label, condition, detail=""):
    global passed
    if not condition:
        raise AssertionError("FAILED: " + label + (" | " + str(detail) if detail else ""))
    passed += 1
    print("PASS  " + label + ((" | " + str(detail)) if detail else ""))


def h(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


def login(username, password):
    response = c.post("/api/v1/user/login", json={"username": username, "password": password})
    ok(f"login {username}", response.status_code == 200, response.status_code)
    return response.json()["access_token"]


def user_id_from_token(token):
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return int(payload["sub"])


def db_counts():
    db = SessionLocal()
    try:
        from models import Post, Spot

        return db.query(Spot).count(), db.query(Post).count()
    finally:
        db.close()


def main():
    print("=== 0. baseline data ===")
    spots_before, posts_before = db_counts()
    print("baseline spots=%s posts=%s" % (spots_before, posts_before))

    print("=== 1. guest auth (expect 401) ===")
    r = c.post("/api/v1/trip/generate", json={"spot_ids": [1, 2], "start_spot_id": 1})
    ok("guest generate -> 401", r.status_code == 401, r.status_code)
    r = c.get("/api/v1/trip/my")
    ok("guest my -> 401", r.status_code == 401, r.status_code)
    r = c.get("/api/v1/trip/1")
    ok("guest detail -> 401", r.status_code == 401, r.status_code)
    r = c.delete("/api/v1/trip/1")
    ok("guest delete -> 401", r.status_code == 401, r.status_code)

    print("=== 2. login and load spots ===")
    user_token = login("favtest1", "abc123")
    admin_token = login("admin", "admin123")
    owner_id = user_id_from_token(user_token)
    admin_id = user_id_from_token(admin_token)
    ok("favtest1 and admin are different users", owner_id != admin_id, (owner_id, admin_id))

    r = c.get("/api/v1/spot/list", params={"page_size": 100})
    ok("spot list -> 200", r.status_code == 200, r.status_code)
    spot_ids = [item["id"] for item in r.json()["items"]]
    ok("at least 3 seeded spots available", len(spot_ids) >= 3, spot_ids)
    spot_ids = spot_ids[:3]

    print("=== 3. generate route ===")
    start_id = spot_ids[0]
    r = c.post(
        "/api/v1/trip/generate",
        json={"spot_ids": spot_ids, "start_spot_id": start_id},
        headers=h(user_token),
    )
    ok("generate with 3 spots -> 200", r.status_code == 200, r.status_code)
    data = r.json()
    route = data["route"]
    ok("route starts at requested start", route[0]["id"] == start_id, route[0]["id"])
    ok("route length >= 3", len(route) >= 3, len(route))
    ok("total_distance > 0", data["total_distance"] > 0, data["total_distance"])
    ok("legs count == route-1", len(data["legs"]) == len(route) - 1, len(data["legs"]))
    ok(
        "every route item has x/y/order",
        all("x" in item and "y" in item and "order" in item for item in route),
    )
    ok(
        "route order is sequential",
        [item["order"] for item in route] == list(range(len(route))),
        [item["order"] for item in route],
    )

    r = c.post(
        "/api/v1/trip/generate",
        json={"spot_ids": [spot_ids[0], 999999], "start_spot_id": spot_ids[0]},
        headers=h(user_token),
    )
    ok("generate with invalid id -> 400", r.status_code == 400, r.status_code)

    r = c.post(
        "/api/v1/trip/generate",
        json={"spot_ids": [spot_ids[0]], "start_spot_id": spot_ids[0]},
        headers=h(user_token),
    )
    ok("generate with 1 spot -> 422", r.status_code == 422, r.status_code)

    outside_start = spot_ids[2]
    r = c.post(
        "/api/v1/trip/generate",
        json={"spot_ids": [spot_ids[0], spot_ids[1]], "start_spot_id": outside_start},
        headers=h(user_token),
    )
    ok("generate with start outside list -> 200", r.status_code == 200, r.status_code)
    ok("outside start is route[0]", r.json()["route"][0]["id"] == outside_start, r.json()["route"][0]["id"])

    print("=== 4. save / list / detail ===")
    r = c.post(
        "/api/v1/trip/save",
        json={"name": "v06 test trip", "spot_ids": spot_ids, "start_spot_id": start_id},
        headers=h(user_token),
    )
    ok("save -> 200", r.status_code == 200, r.status_code)
    trip = r.json()
    trip_id = trip["id"]
    created_trip_ids.append(trip_id)
    ok("saved trip user_id is owner", trip["user_id"] == owner_id, trip["user_id"])

    r = c.post(
        "/api/v1/trip/save",
        json={"name": "", "spot_ids": spot_ids, "start_spot_id": start_id},
        headers=h(user_token),
    )
    ok("save with empty name -> 422", r.status_code == 422, r.status_code)

    r = c.get("/api/v1/trip/my", params={"page": 1, "page_size": 5}, headers=h(user_token))
    ok("my list -> 200", r.status_code == 200, r.status_code)
    listing = r.json()
    ok("my list total >= 1", listing["total"] >= 1, listing["total"])
    ok("my list item has spot_count", "spot_count" in listing["items"][0], listing["items"][0].keys())
    ok(
        "my list item has total_distance",
        "total_distance" in listing["items"][0],
        listing["items"][0].keys(),
    )

    r = c.get("/api/v1/trip/list", params={"page": 1, "page_size": 5}, headers=h(user_token))
    ok("alias /list -> 200", r.status_code == 200, r.status_code)

    r = c.get(f"/api/v1/trip/{trip_id}", headers=h(user_token))
    ok("detail -> 200", r.status_code == 200, r.status_code)
    detail = r.json()
    ok("detail route non-empty", len(detail["route"]) > 0, len(detail["route"]))
    ok("detail user_id matches current user", detail["user_id"] == owner_id, detail["user_id"])

    print("=== 5. cross-user permissions (expect 403) ===")
    r = c.get(f"/api/v1/trip/{trip_id}", headers=h(admin_token))
    ok("admin detail other user -> 403", r.status_code == 403, r.status_code)
    r = c.delete(f"/api/v1/trip/{trip_id}", headers=h(admin_token))
    ok("admin delete other user -> 403", r.status_code == 403, r.status_code)

    print("=== 6. owner delete (expect 200 then 404) ===")
    r = c.delete(f"/api/v1/trip/{trip_id}", headers=h(user_token))
    ok("owner delete -> 200", r.status_code == 200, r.status_code)
    created_trip_ids.remove(trip_id)
    r = c.get(f"/api/v1/trip/{trip_id}", headers=h(user_token))
    ok("detail after delete -> 404", r.status_code == 404, r.status_code)

    print("=== 7. dijkstra unit check (no DB) ===")
    graph = {
        1: {2: 1.0, 4: 10.0},
        2: {1: 1.0, 3: 1.0},
        3: {2: 1.0, 4: 1.0},
        4: {1: 10.0, 3: 1.0},
        5: {},
    }
    path, distance = shortest_path(graph, 1, 4)
    print("detour path=%s distance=%s" % (path, distance))
    ok("dijkstra chooses 2-hop detour", path == [1, 2, 3, 4], path)
    ok("dijkstra exact detour distance is 3.0", abs(distance - 3.0) < 1e-9, distance)

    unreachable_path, unreachable_distance = shortest_path(graph, 1, 5)
    print("unreachable path=%s distance=%s" % (unreachable_path, unreachable_distance))
    ok("unreachable path is empty", unreachable_path == [], unreachable_path)
    ok("unreachable distance is inf", isinf(unreachable_distance) and unreachable_distance == inf, unreachable_distance)

    print("=== 8. cleanup ===")
    for leftover_id in list(created_trip_ids):
        r = c.delete(f"/api/v1/trip/{leftover_id}", headers=h(user_token))
        if r.status_code in (200, 404):
            created_trip_ids.remove(leftover_id)
    ok("all test trips cleaned up", created_trip_ids == [], created_trip_ids)

    spots_after, posts_after = db_counts()
    ok("seeded spots unchanged", spots_after == spots_before, (spots_before, spots_after))
    ok("seeded posts unchanged", posts_after == posts_before, (posts_before, posts_after))

    print("ALL CHECKS PASSED: %s" % passed)


if __name__ == "__main__":
    main()
