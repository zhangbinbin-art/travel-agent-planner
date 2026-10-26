"""只重建 favorites 表的初始化脚本（v0.8）。

为 favorites 增加 (user_id, spot_id) 唯一约束，但绝不触碰其他业务表。
脚本可重复执行：每次 drop 后按最新模型定义 create。
运行后会打印 users / spots / posts / comments / favorites / trips 的行数，
用于证明除 favorites 外的数据没有被改动。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from core.database import SessionLocal, engine
from models import Comment, Favorite, Post, Spot, Trip, User


def row_counts() -> dict:
    """统计各业务表当前行数。"""
    db = SessionLocal()
    try:
        return {
            "users": db.query(func.count(User.id)).scalar() or 0,
            "spots": db.query(func.count(Spot.id)).scalar() or 0,
            "posts": db.query(func.count(Post.id)).scalar() or 0,
            "comments": db.query(func.count(Comment.id)).scalar() or 0,
            "favorites": db.query(func.count(Favorite.id)).scalar() or 0,
            "trips": db.query(func.count(Trip.id)).scalar() or 0,
        }
    finally:
        db.close()


def main():
    print("=== init_favorites start ===")
    before = row_counts()
    print("before:", before)

    # 只重建 favorites 表：不碰 Base.metadata 中的其他表，也不删除任何数据库文件
    Favorite.__table__.drop(bind=engine, checkfirst=True)
    Favorite.__table__.create(bind=engine)
    print("favorites table rebuilt (uq_favorite_user_spot)")

    after = row_counts()
    print("after: ", after)

    for key in ("users", "spots", "posts", "comments", "trips"):
        if before[key] != after[key]:
            print(f"ERROR {key} changed: {before[key]} -> {after[key]}")
            sys.exit(1)
    print("other tables unchanged: OK")
    print("=== init_favorites done ===")


if __name__ == "__main__":
    main()
