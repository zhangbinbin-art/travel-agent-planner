"""posts.custom_spots 列初始化脚本（幂等，可重复执行）。

目标：
1. posts 表缺少 custom_spots 列时补充 `ALTER TABLE posts ADD COLUMN custom_spots TEXT NULL`；
2. 打印实际执行的 DDL 与 posts 最终列清单。

不会 DROP 表、不会修改已有列，也不触碰其他业务表。

用法：
    python scripts/init_post_custom_spots.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import engine
import models  # noqa: F401  确保全部模型注册到 Base.metadata


POSTS_TABLE = "posts"
CUSTOM_SPOTS_COLUMN = "custom_spots"


def ensure_column():
    """posts 表缺 custom_spots 列时补列；返回实际执行的 DDL 列表。"""
    insp = inspect(engine)
    existing = {col["name"] for col in insp.get_columns(POSTS_TABLE)}
    executed = []
    if CUSTOM_SPOTS_COLUMN not in existing:
        ddl = f"ALTER TABLE {POSTS_TABLE} ADD COLUMN {CUSTOM_SPOTS_COLUMN} TEXT NULL"
        with engine.begin() as conn:
            conn.execute(text(ddl))
        executed.append(ddl)
    return executed


def main():
    print("=== init_post_custom_spots start ===")
    print(
        "target:",
        engine.url.render_as_string(hide_password=True),
        "| dialect:",
        engine.dialect.name,
    )

    ddl_list = ensure_column()
    if ddl_list:
        for ddl in ddl_list:
            print("DDL:", ddl)
    else:
        print(f"DDL: none ({POSTS_TABLE}.{CUSTOM_SPOTS_COLUMN} already exists)")

    columns = [col["name"] for col in inspect(engine).get_columns(POSTS_TABLE)]
    print(f"{POSTS_TABLE}.columns:", columns)
    print("=== init_post_custom_spots done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
