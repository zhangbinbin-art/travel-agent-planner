import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

c = TestClient(app)


def h(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


def login(u, p):
    r = c.post("/api/v1/user/login", json={"username": u, "password": p})
    return r.json().get("access_token") if r.status_code == 200 else None


ut = login("favtest1", "abc123")
at = login("admin", "admin123")
print("tokens:", bool(ut), bool(at))

print("=== 1. guest ===")
r = c.get("/api/v1/post/list")
print("list", r.status_code, "total", r.json().get("total"))
r = c.post("/api/v1/post", json={"title": "guest post", "content": "x"})
print("create", r.status_code)

print("=== 2. normal user ===")
r = c.post("/api/v1/post", json={"title": "v05 test post", "content": "hello\nworld"}, headers=h(ut))
print("create", r.status_code)
pid = r.json()["id"]
r = c.get(f"/api/v1/post/{pid}")
print("detail", r.status_code, "author", r.json()["author"]["username"], "comments", len(r.json()["comments"]))
r = c.get("/api/v1/post/list", params={"keyword": "v05"})
print("search", r.status_code, r.json()["total"])
r = c.put(f"/api/v1/post/{pid}", json={"title": "v05 test post edited"}, headers=h(ut))
print("owner update", r.status_code, r.json().get("title"))
r = c.put(f"/api/v1/post/{pid}", json={"title": "v05 edited by admin"}, headers=h(at))
print("admin update", r.status_code, r.json().get("title"))

print("=== 3. comments ===")
r = c.post("/api/v1/comment", params={"post_id": pid}, json={"content": "admin comment", "score": 4}, headers=h(at))
print("admin comment", r.status_code, r.json().get("author", {}).get("username"))
cid_admin = r.json()["id"]
r = c.post("/api/v1/comment", params={"post_id": pid}, json={"content": "owner comment"}, headers=h(ut))
print("owner comment", r.status_code)
cid_owner = r.json()["id"]
r = c.post("/api/v1/comment", params={"post_id": pid}, json={"content": "guest comment"})
print("guest comment", r.status_code)
r = c.get(f"/api/v1/post/{pid}")
print("detail comments", len(r.json()["comments"]), "heat", r.json()["heat"])
r = c.delete(f"/api/v1/comment/{cid_admin}", headers=h(ut))
print("user delete others comment", r.status_code)
r = c.delete(f"/api/v1/comment/{cid_admin}", headers=h(at))
print("admin delete comment", r.status_code)
r = c.delete(f"/api/v1/comment/{cid_owner}", headers=h(ut))
print("owner delete own comment", r.status_code)

print("=== 4. post delete perms ===")
r = c.post("/api/v1/post", json={"title": "admin post", "content": "..."}, headers=h(at))
apid = r.json()["id"]
r = c.delete(f"/api/v1/post/{apid}", headers=h(ut))
print("user delete admin post", r.status_code)
r = c.delete(f"/api/v1/post/{apid}", headers=h(at))
print("admin delete own post", r.status_code)
r = c.delete(f"/api/v1/post/{pid}", headers=h(ut))
print("owner delete own post", r.status_code)
r = c.get(f"/api/v1/post/{pid}")
print("after delete", r.status_code)

print("=== 5. pagination ===")
for i in range(3):
    c.post("/api/v1/post", json={"title": f"page test {i}", "content": "x"}, headers=h(ut))
r = c.get("/api/v1/post/list", params={"page": 1, "page_size": 2})
print(r.status_code, r.json()["page"], r.json()["page_size"], len(r.json()["items"]), r.json()["total"])

for p in c.get("/api/v1/post/list", params={"keyword": "page test", "page_size": 50}).json()["items"]:
    c.delete(f"/api/v1/post/{p['id']}", headers=h(ut))
print("cleanup done")
