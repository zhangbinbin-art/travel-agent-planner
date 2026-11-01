"""posts.images 列与 post_favorites 表初始化脚本（幂等，可重复执行）。

目标：
1. posts 表缺少 images 列时补充 `ALTER TABLE posts ADD COLUMN images TEXT NULL`；
2. 用 Base.metadata.create_all 创建缺失的表（会创建 post_favorites，已存在的表不受影响）；
3. 打印实际执行的 DDL 与 posts 最终列清单。

不会 DROP 表、不会修改已有列，也不触碰其他业务表。SQLite 与 MySQL 均可运行。

用法：
    python scripts/init_post_media.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import Base, engine
import models  # noqa: F401  确保全部模型注册到 Base.metadata


POSTS_TABLE = "posts"
IMAGES_COLUMN = "images"
POST_FAVORITES_TABLE = "post_favorites"


def ensure_columns():
    """posts 表缺 images 列时补列；返回实际执行的 DDL 列表。"""
    insp = inspect(engine)
    existing = {col["name"] for col in insp.get_columns(POSTS_TABLE)}
    executed = []
    if IMAGES_COLUMN not in existing:
        ddl = f"ALTER TABLE {POSTS_TABLE} ADD COLUMN {IMAGES_COLUMN} TEXT NULL"
        with engine.begin() as conn:
            conn.execute(text(ddl))
        executed.append(ddl)
    return executed


def ensure_tables():
    """创建缺失的表；返回本次新建的表名列表。"""
    before = set(inspect(engine).get_table_names())
    Base.metadata.create_all(bind=engine)
    after = set(inspect(engine).get_table_names())
    return sorted(after - before)


def main():
    print("=== init_post_media start ===")
    print(
        "target:",
        engine.url.render_as_string(hide_password=True),
        "| dialect:",
        engine.dialect.name,
    )

    ddl_list = ensure_columns()
    if ddl_list:
        for ddl in ddl_list:
            print("DDL:", ddl)
    else:
        print(f"DDL: none ({POSTS_TABLE}.{IMAGES_COLUMN} already exists)")

    created = ensure_tables()
    if created:
        for table in created:
            print("CREATE TABLE:", table)
    else:
        print("CREATE TABLE: none (all tables already exist)")

    columns = [col["name"] for col in inspect(engine).get_columns(POSTS_TABLE)]
    print(f"{POSTS_TABLE}.columns:", columns)

    tables = inspect(engine).get_table_names()
    print(f"{POST_FAVORITES_TABLE} exists:", POST_FAVORITES_TABLE in tables)
    print("=== init_post_media done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
