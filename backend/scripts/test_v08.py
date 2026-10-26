"""v0.8 自测脚本：收藏唯一约束 + 新版收藏接口 + 门票预算。

运行前请先执行 scripts/init_favorites.py 重建 favorites 表（带唯一约束）。
测试会创建 v08_a / v08_b 两个测试账号，并只清理这两个账号产生的
favorites / trips 数据，绝不触碰其他业务表。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from core.config import settings
from core.database import SessionLocal
from main import app
from models import Favorite, Trip, User

c = TestClient(app)
passed = 0
failed = 0
TEST_USERNAMES = ("v08_a", "v08_b")


def ok(label, condition, detail=""):
    global passed, failed
    if not condition:
        failed += 1
        print("FAIL " + label + (" | " + str(detail) if detail else ""))
        raise AssertionError("FAILED: " + label)
    passed += 1
    print("PASS " + label + ((" | " + str(detail)) if detail else ""))


def h(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


def login(username, password):
    r = c.post("/api/v1/user/login", json={"username": username, "password": password})
    ok(f"login {username}", r.status_code == 200, r.status_code)
    return r.json()["access_token"]


def uid(token):
    return int(jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])["sub"])


def ensure_user(username, password):
    """优先登录，不存在时注册；返回可用 token。"""
    r = c.post("/api/v1/user/login", json={"username": username, "password": password})
    if r.status_code == 200:
        return r.json()["access_token"]
    r = c.post("/api/v1/user/register", json={"username": username, "password": password})
    ok(f"register {username}", r.status_code == 200, r.status_code)
    return login(username, password)


def cleanup_test_users():
    """只清理本脚本创建的 v08_a / v08_b 账号及其 favorites / trips。

    绝不删除其他用户或业务表数据；这样重复运行后数据库与运行前保持一致。
    """
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.username.in_(TEST_USERNAMES)).all()
        ids = [u.id for u in users]
        if ids:
            db.query(Favorite).filter(Favorite.user_id.in_(ids)).delete(synchronize_session=False)
            db.query(Trip).filter(Trip.user_id.in_(ids)).delete(synchronize_session=False)
            for user in users:
                db.delete(user)
            db.commit()
        return ids
    finally:
        db.close()


def main():
    print("=== v08 test start ===")
    cleanup_test_users()

    admin_token = login("admin", "admin123")
    a_token = ensure_user("v08_a", "abc123")
    b_token = ensure_user("v08_b", "abc123")
    a_id = uid(a_token)
    b_id = uid(b_token)
    admin_id = uid(admin_token)
    ok("test users and admin differ", len({a_id, b_id, admin_id}) == 3, (a_id, b_id, admin_id))

    # ---- 游客 401 ----
    r = c.post("/api/v1/favorite/spot/1/favorite")
    ok("guest toggle -> 401", r.status_code == 401, r.status_code)
    r = c.get("/api/v1/favorite/my-favorite-spots")
    ok("guest my-favorite-spots -> 401", r.status_code == 401, r.status_code)

    # ---- 切换收藏：True -> False ----
    r = c.post("/api/v1/favorite/spot/1/favorite", headers=h(a_token))
    ok("toggle spot1 first -> 200", r.status_code == 200, r.status_code)
    d = r.json()
    ok("toggle spot1 favorited true", d.get("favorited") is True, d)
    ok("toggle spot1 favorite_id present", isinstance(d.get("favorite_id"), int), d)
    ok("toggle spot1 echoes spot_id", d.get("spot_id") == 1, d.get("spot_id"))
    ok("toggle spot1 message", d.get("message") == "收藏成功", d.get("message"))
    db = SessionLocal()
    try:
        rows = db.query(Favorite).filter(Favorite.user_id == a_id, Favorite.spot_id == 1).count()
        ok("db row after toggle on", rows == 1, rows)
    finally:
        db.close()

    r = c.post("/api/v1/favorite/spot/1/favorite", headers=h(a_token))
    ok("toggle spot1 second -> 200", r.status_code == 200, r.status_code)
    d = r.json()
    ok("toggle spot1 favorited false", d.get("favorited") is False, d)
    ok("toggle spot1 favorite_id cleared", d.get("favorite_id") is None, d)
    ok("toggle spot1 remove message", d.get("message") == "取消收藏成功", d.get("message"))
    db = SessionLocal()
    try:
        rows = db.query(Favorite).filter(Favorite.user_id == a_id, Favorite.spot_id == 1).count()
        ok("db row after toggle off", rows == 0, rows)
    finally:
        db.close()

    # ---- 收藏两个景点，用于聚合接口与路线预算 ----
    r = c.post("/api/v1/favorite/spot/1/favorite", headers=h(a_token))
    ok("favorite spot1 again", r.status_code == 200 and r.json()["favorited"] is True, r.json())
    r = c.post("/api/v1/favorite/spot/2/favorite", headers=h(a_token))
    ok("favorite spot2", r.status_code == 200 and r.json()["favorited"] is True, r.json())

    r = c.post("/api/v1/favorite/spot/999999/favorite", headers=h(a_token))
    ok("toggle missing spot -> 404", r.status_code == 404, r.status_code)
    ok("toggle missing spot detail", r.json().get("detail") == "景点不存在", r.json())

    # ---- 我的收藏景点聚合 ----
    r = c.get("/api/v1/favorite/my-favorite-spots", headers=h(a_token))
    ok("my-favorite-spots -> 200", r.status_code == 200, r.status_code)
    d = r.json()
    items = d.get("items", [])
    ok("my-favorite-spots total == len", d.get("total") == len(items) == 2, (d.get("total"), len(items)))
    spot_ids = [it["spot_id"] for it in items]
    ok("my-favorite-spots ids", set(spot_ids) == {1, 2}, spot_ids)
    ok("my-favorite-spots newest first", spot_ids == [2, 1], spot_ids)
    ok("my-favorite-spots owned by user a", all(it["user_id"] == a_id for it in items), items)
    ok("my-favorite-spots nested spot payload", all(it.get("spot") and it["spot"].get("name") for it in items), items)
    ok("my-favorite-spots nested id matches", all(it["spot"]["id"] == it["spot_id"] for it in items), items)

    # ---- 数据库唯一约束 ----
    db = SessionLocal()
    try:
        db.add(Favorite(user_id=a_id, spot_id=1))
        raised = False
        try:
            db.commit()
        except IntegrityError:
            raised = True
            db.rollback()
        ok("duplicate favorite raises IntegrityError", raised, "no error")
        rows = db.query(Favorite).filter(Favorite.user_id == a_id, Favorite.spot_id == 1).count()
        ok("duplicate favorite not inserted", rows == 1, rows)
    finally:
        db.close()

    # ---- 收藏 -> 路线生成 -> 预算 ----
    r = c.post(
        "/api/v1/trip/generate",
        json={"spot_ids": [1, 2], "start_spot_id": 1, "days": 3},
        headers=h(a_token),
    )
    ok("generate from favorites -> 200", r.status_code == 200, r.status_code)
    gen = r.json()
    ok("generate route length >= 2", len(gen.get("route", [])) >= 2, len(gen.get("route", [])))
    ok("generate has budget", isinstance(gen.get("budget"), dict), gen.get("budget"))
    budget = gen["budget"]
    ok("budget days echoed", budget.get("days") == 3, budget.get("days"))
    ok("budget items == route spots", len(budget["items"]) == len(gen["route"]), (len(budget["items"]), len(gen["route"])))
    ticket_sum = round(sum(it["ticket_price"] for it in budget["items"]), 2)
    ok("budget ticket_total == sum", budget["ticket_total"] == ticket_sum, (budget["ticket_total"], ticket_sum))
    ok("budget daily_average formula", budget["daily_average"] == round(budget["ticket_total"] / 3, 2), budget)
    ok("budget known spot total 60", budget["ticket_total"] == 60.0, budget["ticket_total"])
    ok("budget item order == route order", [it["spot_id"] for it in budget["items"]] == [s["id"] for s in gen["route"]], budget["items"])
    ok("budget item names == route names", [it["name"] for it in budget["items"]] == [s["name"] for s in gen["route"]], budget["items"])

    r = c.post("/api/v1/trip/generate", json={"spot_ids": [1, 2], "start_spot_id": 1}, headers=h(a_token))
    ok("generate default days -> 200", r.status_code == 200, r.status_code)
    ok("generate default budget days 1", r.json()["budget"]["days"] == 1, r.json()["budget"]["days"])
    r = c.post("/api/v1/trip/generate", json={"spot_ids": [1, 2], "start_spot_id": 1, "days": 0}, headers=h(a_token))
    ok("generate days 0 -> 422", r.status_code == 422, r.status_code)

    # ---- 兼容旧的收藏接口 ----
    r = c.post("/api/v1/favorite", params={"spot_id": 3}, headers=h(a_token))
    ok("legacy add favorite -> 200", r.status_code == 200, r.status_code)
    ok("legacy add message", r.json().get("message") == "收藏成功", r.json())
    r = c.delete("/api/v1/favorite", params={"spot_id": 3}, headers=h(a_token))
    ok("legacy remove favorite -> 200", r.status_code == 200, r.status_code)
    ok("legacy remove message", r.json().get("message") == "取消收藏成功", r.json())
    r = c.get("/api/v1/favorite/my", headers=h(a_token))
    ok("legacy my favorites -> 200", r.status_code == 200, r.status_code)
    legacy_my = r.json()
    ok("legacy my favorites total 2", legacy_my.get("total") == 2, legacy_my.get("total"))
    ok("legacy my favorites items 2", len(legacy_my.get("items", [])) == 2, len(legacy_my.get("items", [])))

    # ---- 保存路线：days + budget 持久化 ----
    r = c.post(
        "/api/v1/trip/save",
        json={"name": "v08 trip", "spot_ids": [1, 2], "start_spot_id": 1, "days": 3},
        headers=h(a_token),
    )
    ok("save trip -> 200", r.status_code == 200, r.status_code)
    saved = r.json()
    trip_id = saved["id"]
    ok("saved trip days 3", saved.get("days") == 3, saved.get("days"))
    ok("saved trip budget present", isinstance(saved.get("budget"), dict), saved.get("budget"))
    ok("saved trip budget days 3", saved["budget"].get("days") == 3, saved["budget"])
    ok("saved trip spot_count == route", saved["spot_count"] == len(saved["route"]), (saved["spot_count"], len(saved["route"])))
    ok("saved trip budget items == route", len(saved["budget"]["items"]) == len(saved["route"]), saved["budget"])
    db = SessionLocal()
    try:
        stored = db.query(Trip).filter(Trip.id == trip_id).first()
        payload = json.loads(stored.route_json)
        ok("stored route_json has days", payload.get("days") == 3, payload.get("days"))
        ok("stored route_json has budget", isinstance(payload.get("budget"), dict), payload.get("budget"))
    finally:
        db.close()

    # ---- 越权访问 ----
    r = c.get(f"/api/v1/trip/{trip_id}", headers=h(b_token))
    ok("user B reads A trip -> 403", r.status_code == 403, r.status_code)
    ok("user B forbidden message", r.json().get("detail") == "无权限操作", r.json())
    r = c.get(f"/api/v1/trip/{trip_id}", headers=h(admin_token))
    ok("admin reads other user trip -> 403", r.status_code == 403, r.status_code)
    r = c.get("/api/v1/favorite/my-favorite-spots", headers=h(admin_token))
    ok("admin my-favorite-spots -> 200", r.status_code == 200, r.status_code)
    admin_items = r.json().get("items", [])
    ok("admin favorites only own rows", all(it["user_id"] == admin_id for it in admin_items), admin_items)
    ok("admin favorites total == len", r.json().get("total") == len(admin_items), r.json().get("total"))

    # ---- 我的路线列表：days + budget ----
    r = c.get("/api/v1/trip/my", headers=h(a_token))
    ok("trip list -> 200", r.status_code == 200, r.status_code)
    listed = r.json().get("items", [])
    ok("trip list contains saved trip", any(it["id"] == trip_id for it in listed), [it["id"] for it in listed])
    ok("trip list items all have budget", all(isinstance(it.get("budget"), dict) for it in listed), listed)
    ok("trip list items all have days", all(it.get("days", 0) >= 1 for it in listed), listed)

    # ---- 旧版路线（route_json 无 days/budget）仍能算出预算 ----
    legacy_payload = {
        "spot_ids": [s["id"] for s in gen["route"]],
        "start_spot_id": 1,
        "route": gen["route"],
        "legs": gen["legs"],
    }
    db = SessionLocal()
    try:
        legacy_trip = Trip(
            user_id=a_id,
            name="v08 legacy no budget",
            route_json=json.dumps(legacy_payload, ensure_ascii=False),
            total_distance=gen.get("total_distance", 0),
        )
        db.add(legacy_trip)
        db.commit()
        db.refresh(legacy_trip)
        legacy_trip_id = legacy_trip.id
    finally:
        db.close()

    r = c.get(f"/api/v1/trip/{legacy_trip_id}", headers=h(a_token))
    ok("legacy trip detail -> 200", r.status_code == 200, r.status_code)
    legacy_detail = r.json()
    ok("legacy trip days fallback 1", legacy_detail.get("days") == 1, legacy_detail.get("days"))
    ok("legacy trip budget computed", isinstance(legacy_detail.get("budget"), dict), legacy_detail.get("budget"))
    legacy_budget = legacy_detail["budget"]
    ok("legacy trip budget item count", len(legacy_budget["items"]) == len(legacy_detail["route"]), legacy_budget)
    legacy_expected = round(sum(it["ticket_price"] for it in legacy_budget["items"]), 2)
    ok("legacy trip ticket_total", legacy_budget["ticket_total"] == legacy_expected, legacy_budget)
    ok("legacy trip daily_average", legacy_budget["daily_average"] == round(legacy_expected / 1, 2), legacy_budget)

    # ---- 清理本脚本创建的数据 ----
    cleanup_test_users()
    print(f"=== DONE: PASS={passed} FAIL={failed} ===")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # 失败时也清理测试账号产生的数据，避免污染下一次运行
        cleanup_test_users()
        print(f"=== ABORTED: PASS={passed} FAIL={failed} ===")
        raise
