"""安全删除景点：先清理/合并关联数据，再删除 spots 记录。

背景：
    spots 被 comments.spot_id、favorites.spot_id 外键引用，直接删除会触发
    IntegrityError（管理员页面表现为删除失败/500）。本脚本先处理引用再删除，
    并支持把关联数据合并到另一个景点（推荐做法，避免丢失点评）。

用法：
    python scripts/delete_spot_safe.py --name 迪士尼乐园                      # 预览
    python scripts/delete_spot_safe.py --name 迪士尼乐园 --merge-into 上海迪士尼乐园 --apply
    python scripts/delete_spot_safe.py --id 9 --apply                        # 直接删除（引用置空/移除）
    python scripts/delete_spot_safe.py --name 迪士尼乐园 --merge-into 24 --apply --force-trips

处理内容：
    1. comments.spot_id  -> 合并目标 id（无目标时置 NULL）
    2. favorites         -> 合并目标（同一用户重复收藏去重）
    3. posts.spot_ids    -> JSON 数组里替换为目标 id 或移除
    4. trips.route_json  -> 默认只统计并阻止删除；加 --force-trips 时重写 id 并去重
    5. 最后删除 spots 记录
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models import Comment, Favorite, Post, Spot, Trip


def _load_json(raw, default):
    try:
        data = json.loads(raw) if raw else default
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def find_spot(db, spot_id=None, name=None):
    if spot_id:
        return db.query(Spot).filter(Spot.id == spot_id).first()
    return db.query(Spot).filter(Spot.name == name).first()


def remap_posts(db, target_id, merge_id):
    changed = 0
    for post in db.query(Post).all():
        ids = _load_json(post.spot_ids, [])
        if not ids or target_id not in ids:
            continue
        new_ids = []
        for sid in ids:
            sid = merge_id if sid == target_id else sid
            if sid is not None and sid not in new_ids:
                new_ids.append(sid)
        post.spot_ids = json.dumps(new_ids, ensure_ascii=False)
        changed += 1
    return changed


def remap_favorites(db, target_id, merge_id):
    rows = db.query(Favorite).filter(Favorite.spot_id == target_id).all()
    if not rows:
        return 0, 0
    if merge_id is None:
        for row in rows:
            db.delete(row)
        return 0, len(rows)
    existing = {(f.user_id, f.spot_id) for f in db.query(Favorite).all()}
    moved, dropped = 0, 0
    for row in rows:
        if (row.user_id, merge_id) in existing:
            db.delete(row)
            dropped += 1
        else:
            row.spot_id = merge_id
            existing.add((row.user_id, merge_id))
            moved += 1
    return moved, dropped


def remap_comments(db, target_id, merge_id):
    rows = db.query(Comment).filter(Comment.spot_id == target_id).all()
    for row in rows:
        row.spot_id = merge_id
    return len(rows)


def remap_trips(db, target_id, merge_id):
    affected = []
    for trip in db.query(Trip).all():
        payload = _load_json(trip.route_json, {})
        route = payload.get("route") or []
        if not any(item.get("id") == target_id for item in route):
            continue
        affected.append(trip)
    return affected


def rewrite_trips(affected, target_id, merge_id):
    for trip in affected:
        payload = _load_json(trip.route_json, {})
        spot_ids = payload.get("spot_ids") or []
        new_ids = []
        for sid in spot_ids:
            sid = merge_id if sid == target_id else sid
            if sid is not None and sid not in new_ids:
                new_ids.append(sid)

        seen = set()
        new_route = []
        for item in payload.get("route") or []:
            sid = merge_id if item.get("id") == target_id else item.get("id")
            if sid is None or sid in seen:
                continue
            seen.add(sid)
            item["id"] = sid
            new_route.append(item)
        for order, item in enumerate(new_route):
            item["order"] = order

        new_legs = []
        for leg in payload.get("legs") or []:
            f = merge_id if leg.get("from_spot_id") == target_id else leg.get("from_spot_id")
            t = merge_id if leg.get("to_spot_id") == target_id else leg.get("to_spot_id")
            if f is None or t is None or f == t:
                continue
            new_legs.append({"from_spot_id": f, "to_spot_id": t, "distance": leg.get("distance", 0)})

        payload["spot_ids"] = new_ids
        payload["route"] = new_route
        payload["legs"] = new_legs
        trip.route_json = json.dumps(payload, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int)
    parser.add_argument("--name")
    parser.add_argument("--merge-into", dest="merge_into", help="合并目标：景点 id 或名称")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force-trips", action="store_true", help="允许重写已保存路线中的引用")
    args = parser.parse_args()

    if not args.id and not args.name:
        print("[ERROR] 需要 --id 或 --name")
        return 2

    db = SessionLocal()
    spot = find_spot(db, args.id, args.name)
    if not spot:
        print("[ERROR] 未找到景点")
        return 2

    merge_spot = None
    if args.merge_into:
        merge_spot = find_spot(db, None, args.merge_into)
        if not merge_spot and str(args.merge_into).isdigit():
            merge_spot = find_spot(db, int(args.merge_into), None)
        if not merge_spot:
            print("[ERROR] 合并目标不存在：", args.merge_into)
            return 2
        if merge_spot.id == spot.id:
            print("[ERROR] 合并目标不能是自己")
            return 2

    merge_id = merge_spot.id if merge_spot else None
    comments = db.query(Comment).filter(Comment.spot_id == spot.id).count()
    favorites = db.query(Favorite).filter(Favorite.spot_id == spot.id).count()
    posts = [p for p in db.query(Post).all() if p.spot_ids and spot.id in _load_json(p.spot_ids, [])]
    trips = remap_trips(db, spot.id, merge_id)

    print("=== 待删除景点 ===")
    print("id=%s 名称=%s 城市=%s" % (spot.id, spot.name, spot.city))
    print("关联评论：%d 条 | 关联收藏：%d 条 | 关联帖子：%d 篇 | 关联路线：%d 条" % (
        comments, favorites, len(posts), len(trips)))
    print("合并目标：", ("%s（id=%s）" % (merge_spot.name, merge_spot.id)) if merge_spot else "无（引用将置空/移除）")

    if trips and not args.force_trips:
        print("[BLOCK] 有已保存路线引用该景点，确认要重写请加 --force-trips")
        return 1

    if not args.apply:
        print("\nDRY-RUN 结束，加 --apply 才会执行。")
        return 0

    moved_comments = remap_comments(db, spot.id, merge_id)
    moved_fav, dropped_fav = remap_favorites(db, spot.id, merge_id)
    touched_posts = remap_posts(db, spot.id, merge_id)
    if trips:
        rewrite_trips(trips, spot.id, merge_id)
    db.delete(spot)
    db.commit()

    print("\n=== 执行结果 ===")
    print("迁移评论：%d 条" % moved_comments)
    print("迁移收藏：%d 条（去重删除 %d 条）" % (moved_fav, dropped_fav))
    print("更新帖子引用：%d 篇" % touched_posts)
    print("重写路线：%d 条" % len(trips))
    print("已删除景点：%s（id=%s）" % (spot.name, spot.id))
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
