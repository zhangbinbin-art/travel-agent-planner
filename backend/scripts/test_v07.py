import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt
from fastapi.testclient import TestClient
from core.config import settings
from core.database import SessionLocal
from main import app
from models import Post, Comment, PostLike, CommentLike, User

c = TestClient(app)
passed = 0
failed = 0
created_post_ids = []


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


def make_post(token, title, spot_ids=None):
    body = {"title": title, "content": "content", "cover": "https://picsum.photos/seed/t/800/450"}
    if spot_ids is not None:
        body["spot_ids"] = spot_ids
    r = c.post("/api/v1/post", json=body, headers=h(token))
    ok("create post " + title, r.status_code == 200, r.status_code)
    pid = r.json()["id"]
    created_post_ids.append(pid)
    return pid


def approve_post(admin_token, pid):
    r = c.put(f"/api/v1/admin/post/{pid}/review", json={"status": 1}, headers=h(admin_token))
    ok("approve post " + str(pid), r.status_code == 200, r.status_code)


def preclean():
    db = SessionLocal()
    try:
        leftovers = db.query(Post).filter(Post.title.like("v07 %")).all()
        for p in leftovers:
            db.query(CommentLike).filter(CommentLike.comment_id.in_(db.query(Comment.id).filter(Comment.post_id == p.id))).delete(synchronize_session=False)
            db.query(Comment).filter(Comment.post_id == p.id).delete(synchronize_session=False)
            db.query(PostLike).filter(PostLike.post_id == p.id).delete(synchronize_session=False)
            db.delete(p)
        db.commit()
    finally:
        db.close()


def main():
    print("=== v07 test start ===")
    preclean()
    user_token = login("favtest1", "abc123")
    admin_token = login("admin", "admin123")
    user_id = uid(user_token)
    admin_id = uid(admin_token)
    ok("user and admin differ", user_id != admin_id, (user_id, admin_id))

    # ---- guest auth ----
    r = c.post("/api/v1/post", json={"title": "t"})
    ok("guest create -> 401", r.status_code == 401, r.status_code)
    r = c.post("/api/v1/post/1/like")
    ok("guest like -> 401", r.status_code == 401, r.status_code)
    r = c.post("/api/v1/post/1/comment", json={"content": "hi"})
    ok("guest comment -> 401", r.status_code == 401, r.status_code)
    r = c.post("/api/v1/comment/1/like")
    ok("guest comment like -> 401", r.status_code == 401, r.status_code)

    # ---- guest list only status 1 ----
    r = c.get("/api/v1/post/list", params={"page_size": 100})
    ok("guest list -> 200", r.status_code == 200, r.status_code)
    data = r.json()
    ok("guest list has items", len(data.get("items", [])) > 0, len(data.get("items", [])))
    for item in data.get("items", []):
        ok("guest sees only status 1", item.get("status") == 1, item.get("status"))
    ok("guest list total matches items", data["total"] >= len(data["items"]), (data["total"], len(data["items"])))

    # ---- create a fresh post for like/comment tests ----
    pid = make_post(user_token, "v07 like test post", spot_ids=[1])
    r = c.get(f"/api/v1/post/{pid}", headers=h(user_token))
    ok("owner can read pending post", r.status_code == 200, r.status_code)
    ok("new post status 0", r.json()["status"] == 0, r.json()["status"])
    ok("new post status_text", r.json()["status_text"] == "待审核", r.json()["status_text"])
    r = c.get(f"/api/v1/post/{pid}")
    ok("guest cannot read pending post -> 404", r.status_code == 404, r.status_code)
    r = c.post(f"/api/v1/post/{pid}/like", headers=h(user_token))
    ok("like pending post -> 400", r.status_code == 400, r.status_code)
    r = c.post(f"/api/v1/post/{pid}/comment", json={"content": "x"}, headers=h(user_token))
    ok("comment pending post -> 400", r.status_code == 400, r.status_code)

    approve_post(admin_token, pid)

    # ---- like idempotency ----
    r = c.post(f"/api/v1/post/{pid}/like", headers=h(user_token))
    ok("like first -> 200", r.status_code == 200, r.status_code)
    res1 = r.json()
    ok("liked true", res1.get("liked") is True, res1)
    ok("like_count 1", res1.get("like_count") == 1, res1)
    r = c.post(f"/api/v1/post/{pid}/like", headers=h(user_token))
    res2 = r.json()
    ok("liked false after toggle", res2.get("liked") is False, res2)
    ok("like_count 0 after toggle", res2.get("like_count") == 0, res2)
    r = c.post(f"/api/v1/post/{pid}/like", headers=h(user_token))
    res3 = r.json()
    ok("liked true third time", res3.get("liked") is True, res3)
    ok("like_count 1 third time", res3.get("like_count") == 1, res3)
    db = SessionLocal()
    try:
        rows = db.query(PostLike).filter(PostLike.post_id == pid, PostLike.user_id == user_id).count()
        ok("no duplicate like rows", rows == 1, rows)
        p = db.query(Post).filter(Post.id == pid).first()
        ok("heat consistent after like", p.heat == p.like_count * 2 + p.view_count + p.comment_count * 2, (p.heat, p.like_count, p.view_count, p.comment_count))
    finally:
        db.close()

    # ---- comment create -> status 0, not public ----
    r = c.post(f"/api/v1/post/{pid}/comment", json={"content": "v07 test comment", "score": 5}, headers=h(user_token))
    ok("create comment -> 200", r.status_code == 200, r.status_code)
    cdata = r.json()
    cid = cdata["id"]
    ok("new comment status 0", cdata.get("status") == 0, cdata.get("status"))
    ok("new comment status_text", cdata.get("status_text") == "待审核", cdata.get("status_text"))
    ok("new comment like_count 0", cdata.get("like_count") == 0, cdata.get("like_count"))
    r = c.get(f"/api/v1/post/{pid}/comment-list")
    ok("public comment-list -> 200", r.status_code == 200, r.status_code)
    ids_public = [it["id"] for it in r.json().get("items", [])]
    ok("status 0 comment not visible publicly", cid not in ids_public, ids_public)
    r = c.get(f"/api/v1/post/{pid}/comment-list", headers=h(user_token))
    ids_own = [it["id"] for it in r.json().get("items", [])]
    ok("author sees own pending comment", cid in ids_own, ids_own)

    # ---- admin review comment approve -> visible ----
    r = c.put(f"/api/v1/admin/comment/{cid}/review", json={"status": 1}, headers=h(admin_token))
    ok("admin approve comment -> 200", r.status_code == 200, r.status_code)
    ok("approved comment status 1", r.json().get("status") == 1, r.json().get("status"))
    r = c.get(f"/api/v1/post/{pid}/comment-list")
    ids_public2 = [it["id"] for it in r.json().get("items", [])]
    ok("approved comment visible", cid in ids_public2, ids_public2)

    # ---- comment like toggle ----
    r = c.post(f"/api/v1/comment/{cid}/like", headers=h(user_token))
    ok("comment like -> 200", r.status_code == 200, r.status_code)
    ok("comment liked true", r.json().get("liked") is True, r.json())
    ok("comment like_count 1", r.json().get("like_count") == 1, r.json())
    r = c.post(f"/api/v1/comment/{cid}/like", headers=h(user_token))
    ok("comment liked false after toggle", r.json().get("liked") is False, r.json())
    ok("comment like_count 0 after toggle", r.json().get("like_count") == 0, r.json())
    r = c.post("/api/v1/comment/999999/like", headers=h(user_token))
    ok("comment like missing -> 404", r.status_code == 404, r.status_code)

    # ---- legacy comment endpoint ----
    r = c.post("/api/v1/comment", params={"post_id": pid}, json={"content": "legacy comment"}, headers=h(user_token))
    ok("legacy comment -> 200", r.status_code == 200, r.status_code)
    legacy_cid = r.json()["id"]
    ok("legacy comment status 0", r.json().get("status") == 0, r.json().get("status"))

    # ---- non-owner PUT/DELETE 403 ----
    r = c.post("/api/v1/user/login", json={"username": "favtest2", "password": "abc123"})
    ok("login favtest2", r.status_code == 200, r.status_code)
    user2_token = r.json()["access_token"]
    r = c.put(f"/api/v1/post/{pid}", json={"title": "x"}, headers=h(user2_token))
    ok("non-owner put -> 403", r.status_code == 403, r.status_code)
    ok("non-owner put message", r.json().get("detail") == "无权限操作", r.json())
    r = c.delete(f"/api/v1/post/{pid}", headers=h(user2_token))
    ok("non-owner delete -> 403", r.status_code == 403, r.status_code)

    # ---- owner update resets status ----
    r = c.put(f"/api/v1/post/{pid}", json={"title": "v07 edited"}, headers=h(user_token))
    ok("owner update -> 200", r.status_code == 200, r.status_code)
    ok("owner update resets status 0", r.json().get("status") == 0, r.json().get("status"))
    approve_post(admin_token, pid)
    r = c.put(f"/api/v1/post/{pid}", json={"title": "v07 admin edited"}, headers=h(admin_token))
    ok("admin update keeps status 1", r.json().get("status") == 1, r.json().get("status"))

    # ---- admin list ----
    r = c.get("/api/v1/admin/post/list", headers=h(user_token))
    ok("admin list 403 for normal user", r.status_code == 403, r.status_code)
    ok("admin list message", r.json().get("detail") == "Admin required", r.json())
    r = c.get("/api/v1/admin/post/list", headers=h(admin_token))
    ok("admin list -> 200", r.status_code == 200, r.status_code)
    ok("admin list sees all statuses", any(it["status"] == 0 for it in r.json()["items"]) or r.json()["total"] > 0, r.json()["total"])
    r = c.get("/api/v1/admin/post/list", params={"status": 0}, headers=h(admin_token))
    ok("admin list status filter -> 200", r.status_code == 200, r.status_code)
    for it in r.json()["items"]:
        ok("admin status filter respected", it["status"] == 0, it["status"])
    r = c.get("/api/v1/admin/comment/list", headers=h(admin_token))
    ok("admin comment list -> 200", r.status_code == 200, r.status_code)
    r = c.get("/api/v1/admin/comment/list", headers=h(user_token))
    ok("admin comment list 403 for normal user", r.status_code == 403, r.status_code)

    # ---- review validation ----
    r = c.put(f"/api/v1/admin/post/{pid}/review", json={"status": 3}, headers=h(admin_token))
    ok("review status 3 -> 422", r.status_code == 422, r.status_code)
    r = c.put(f"/api/v1/admin/post/{pid}/review", json={"status": 0}, headers=h(admin_token))
    ok("review status 0 -> 422", r.status_code == 422, r.status_code)
    r = c.put("/api/v1/admin/post/999999/review", json={"status": 1}, headers=h(admin_token))
    ok("review missing post -> 404", r.status_code == 404, r.status_code)
    r = c.put("/api/v1/admin/comment/999999/review", json={"status": 1}, headers=h(admin_token))
    ok("review missing comment -> 404", r.status_code == 404, r.status_code)

    # ---- list filters ----
    r = c.get("/api/v1/post/list", params={"sort": "hot", "page_size": 100})
    ok("hot sort -> 200", r.status_code == 200, r.status_code)
    heats = [it["heat"] for it in r.json()["items"]]
    ok("hot sort descending", heats == sorted(heats, reverse=True), heats)
    r = c.get("/api/v1/post/list", params={"keyword": "v07 admin edited", "page_size": 100})
    ok("keyword filter -> 200", r.status_code == 200, r.status_code)
    ok("keyword filter finds post", any(it["id"] == pid for it in r.json()["items"]), r.json()["total"])
    r = c.get("/api/v1/post/list", params={"spot_id": 1, "page_size": 100})
    ok("spot_id filter -> 200", r.status_code == 200, r.status_code)
    for it in r.json()["items"]:
        ok("spot_id filter respected", 1 in it["spot_ids"], it["spot_ids"])
    r = c.get("/api/v1/post/list", params={"status": 0})
    ok("guest status param ignored -> 200", r.status_code == 200, r.status_code)
    for it in r.json()["items"]:
        ok("guest forced status 1", it["status"] == 1, it["status"])
    r = c.get("/api/v1/post/list", params={"status": 9}, headers=h(admin_token))
    ok("admin invalid status -> 422", r.status_code == 422, r.status_code)

    # ---- sentiment ----
    r = c.get("/api/v1/post/spot/1/sentiment")
    ok("sentiment -> 200", r.status_code == 200, r.status_code)
    sd = r.json()
    ok("sentiment spot_id", sd.get("spot_id") == 1, sd.get("spot_id"))
    ok("sentiment has all keys", all(k in sd for k in ["spot_id", "total", "positive", "neutral", "negative", "positive_percent", "neutral_percent", "negative_percent"]), sd)
    ssum = round(sd["positive_percent"] + sd["neutral_percent"] + sd["negative_percent"], 2)
    ok("sentiment percents sum to 100", abs(ssum - 100.0) < 1e-9, ssum)
    ok("sentiment total>0 after seed", sd["total"] > 0, sd["total"])
    ok("sentiment counts sum to total", sd["positive"] + sd["neutral"] + sd["negative"] == sd["total"], sd)
    r = c.get("/api/v1/post/spot/99999/sentiment")
    ok("empty spot sentiment -> 200", r.status_code == 200, r.status_code)
    sd2 = r.json()
    ok("empty spot total 0", sd2["total"] == 0, sd2["total"])
    ok("empty spot percents 0", sd2["positive_percent"] == 0.0 and sd2["neutral_percent"] == 0.0 and sd2["negative_percent"] == 0.0, sd2)
    r = c.get("/api/v1/post/spot/1/sentiment")
    ok("spot sentiment route not shadowed", r.status_code == 200 and "spot_id" in r.json(), r.status_code)

    # ---- delete cascade ----
    pdid = make_post(user_token, "v07 cascade post", spot_ids=[1])
    approve_post(admin_token, pdid)
    r = c.post(f"/api/v1/post/{pdid}/comment", json={"content": "cascade comment"}, headers=h(user_token))
    cdel = r.json()
    c.put(f"/api/v1/admin/comment/{cdel['id']}/review", json={"status": 1}, headers=h(admin_token))
    c.post(f"/api/v1/post/{pdid}/like", headers=h(user_token))
    c.post(f"/api/v1/comment/{cdel['id']}/like", headers=h(user_token))
    db = SessionLocal()
    try:
        ok("cascade setup post likes", db.query(PostLike).filter(PostLike.post_id == pdid).count() >= 1, db.query(PostLike).filter(PostLike.post_id == pdid).count())
        ok("cascade setup comments", db.query(Comment).filter(Comment.post_id == pdid).count() >= 1, db.query(Comment).filter(Comment.post_id == pdid).count())
        ok("cascade setup comment likes", db.query(CommentLike).filter(CommentLike.comment_id == cdel["id"]).count() >= 1, db.query(CommentLike).filter(CommentLike.comment_id == cdel["id"]).count())
    finally:
        db.close()
    r = c.delete(f"/api/v1/post/{pdid}", headers=h(admin_token))
    ok("admin delete others post -> 200", r.status_code == 200, r.status_code)
    ok("delete message", r.json().get("message") == "删除成功", r.json())
    if pdid in created_post_ids:
        created_post_ids.remove(pdid)
    db = SessionLocal()
    try:
        ok("post likes gone", db.query(PostLike).filter(PostLike.post_id == pdid).count() == 0, db.query(PostLike).filter(PostLike.post_id == pdid).count())
        ok("comments gone", db.query(Comment).filter(Comment.post_id == pdid).count() == 0, db.query(Comment).filter(Comment.post_id == pdid).count())
        ok("comment likes gone", db.query(CommentLike).filter(CommentLike.comment_id == cdel["id"]).count() == 0, db.query(CommentLike).filter(CommentLike.comment_id == cdel["id"]).count())
        ok("post row gone", db.query(Post).filter(Post.id == pdid).count() == 0, db.query(Post).filter(Post.id == pdid).count())
    finally:
        db.close()
    r = c.get(f"/api/v1/post/{pdid}", headers=h(admin_token))
    ok("deleted post detail -> 404", r.status_code == 404, r.status_code)

    # ---- cleanup ----
    for leftover in list(created_post_ids):
        c.delete(f"/api/v1/post/{leftover}", headers=h(admin_token))
        created_post_ids.remove(leftover)

    print(f"=== DONE: PASS={passed} FAIL={failed} ===")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
