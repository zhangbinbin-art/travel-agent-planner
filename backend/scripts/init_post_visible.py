"""posts.visible 列初始化脚本（幂等，可重复执行）

目标：
1. posts 表缺少 visible 列时执行
   `ALTER TABLE posts ADD COLUMN visible VARCHAR(16) NOT NULL DEFAULT 'public'`
2. 打印实际执行的 DDL 与 posts 表字段清单

说明：不含 DROP，不修改已有列，不影响业务数据；旧数据自动落为 public。

用法：
    python scripts/init_post_visible.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import engine
import models  # noqa: F401  确保全部模型注册到 Base.metadata


POSTS_TABLE = "posts"
VISIBLE_COLUMN = "visible"


def ensure_column():
    insp = inspect(engine)
    existing = {col["name"] for col in insp.get_columns(POSTS_TABLE)}
    executed = []
    if VISIBLE_COLUMN not in existing:
        ddl = (
            f"ALTER TABLE {POSTS_TABLE} ADD COLUMN {VISIBLE_COLUMN} "
            "VARCHAR(16) NOT NULL DEFAULT 'public'"
        )
        with engine.begin() as conn:
            conn.execute(text(ddl))
        executed.append(ddl)
    return executed


def main():
    print("=== init_post_visible start ===")
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
        print(f"DDL: none ({POSTS_TABLE}.{VISIBLE_COLUMN} already exists)")

    columns = [col["name"] for col in inspect(engine).get_columns(POSTS_TABLE)]
    print(f"{POSTS_TABLE}.columns:", columns)
    print("=== init_post_visible done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
