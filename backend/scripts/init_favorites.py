"""favorites 表初始化脚本（v0.8 起；v0.9 改为幂等、不删表）。

目标：确保 favorites 表存在、带 (user_id, spot_id) 唯一约束，然后清空该表数据。
不会 DROP 表、不会删除库文件，也不触碰 users / spots / posts / comments / trips。
脚本可重复执行，多次运行结果一致（幂等）；SQLite 与 MySQL 均可运行。

注意：本脚本会清空 favorites 表中的全部收藏记录（表结构与索引保留）。
为避免误跑，必须显式传入 --yes 才会执行；不带 --yes 时只打印警告并退出，
不会建立表结构、也不会执行 DELETE。

用法：
    python scripts/init_favorites.py --yes
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, inspect, text

from core.database import SessionLocal, engine
from models import Comment, Favorite, Post, Spot, Trip, User

UNIQUE_NAME = "uq_favorite_user_spot"
PAIR_COLUMNS = {"user_id", "spot_id"}


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


def safe_url() -> str:
    """打印用连接串，密码以 *** 代替。"""
    return engine.url.render_as_string(hide_password=True)


def has_unique_pair(insp) -> bool:
    """是否已存在覆盖 (user_id, spot_id) 的唯一约束或唯一索引。"""
    for uc in insp.get_unique_constraints(Favorite.__tablename__):
        if set(uc.get("column_names") or []) == PAIR_COLUMNS:
            return True
    for ix in insp.get_indexes(Favorite.__tablename__):
        if ix.get("unique") and set(ix.get("column_names") or []) == PAIR_COLUMNS:
            return True
    return False


def ensure_favorites_table() -> str:
    """建表（若不存在）并确保唯一约束存在；绝不删除已有结构。"""
    table = Favorite.__table__
    table.create(bind=engine, checkfirst=True)

    insp = inspect(engine)
    if has_unique_pair(insp):
        return "table ready, unique(user_id, spot_id) present"

    # SQLite 不支持 ALTER TABLE ADD CONSTRAINT，用同名唯一索引达到等价约束；
    # MySQL 等支持方言直接加表级唯一约束。
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(text(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {UNIQUE_NAME} "
                f"ON {table.name} (user_id, spot_id)"
            ))
        else:
            conn.execute(text(
                f"ALTER TABLE {table.name} ADD CONSTRAINT {UNIQUE_NAME} "
                f"UNIQUE (user_id, spot_id)"
            ))
    return "unique(user_id, spot_id) created"


def clear_favorites() -> int:
    """清空 favorites 数据，保留表结构与索引；返回删除行数。"""
    with engine.begin() as conn:
        result = conn.execute(text(f"DELETE FROM {Favorite.__tablename__}"))
    deleted = result.rowcount
    return deleted if isinstance(deleted, int) and deleted > 0 else 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="初始化 favorites 表：确保表与唯一约束存在，并清空收藏数据（表结构保留）"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="确认清空 favorites 表的全部数据；不传则只打印警告并退出，不做任何修改",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    print("=== init_favorites start ===")
    print("target:", safe_url(), "| dialect:", engine.dialect.name)

    if not args.yes:
        print("WARNING: 该脚本会清空 favorites 表的全部收藏数据（表结构与索引保留）。")
        print("WARNING: 未传入 --yes，已退出，未建立表结构、未执行任何 DELETE。")
        print("hint: 确认无误后执行 -> python scripts/init_favorites.py --yes")
        return 2

    # 先确保表存在，再做统计：新库/表缺失时 row_counts 才不会因 no such table 崩溃
    print("schema:", ensure_favorites_table())

    before = row_counts()
    print("before:", before)

    deleted = clear_favorites()
    print("favorites cleared:", deleted, "row(s) deleted")

    after = row_counts()
    print("after: ", after)

    failed = False
    for key in ("users", "spots", "posts", "comments", "trips"):
        if before[key] != after[key]:
            print(f"ERROR {key} changed: {before[key]} -> {after[key]}")
            failed = True
    if after["favorites"] != 0:
        print(f"ERROR favorites not empty: {after['favorites']}")
        failed = True
    if not has_unique_pair(inspect(engine)):
        print("ERROR unique(user_id, spot_id) missing after init")
        failed = True
    if failed:
        sys.exit(1)
    print("other tables unchanged: OK")
    print("favorites empty + unique constraint intact: OK")
    print("=== init_favorites done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
