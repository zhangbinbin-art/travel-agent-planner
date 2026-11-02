"""建社交模块表：follows / messages（幂等，可重复执行）。

用法：
    python scripts/init_social.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect

from core.database import Base, engine
import models  # noqa: F401  确保模型注册到 Base.metadata
from models import Follow, Message


def main():
    print("=== init_social start ===")
    print("target:", engine.url.render_as_string(hide_password=True), "| dialect:", engine.dialect.name)

    before = set(inspect(engine).get_table_names())
    Base.metadata.create_all(bind=engine, tables=[Follow.__table__, Message.__table__])
    after = set(inspect(engine).get_table_names())

    for table in ("follows", "messages"):
        print(f"{table}: {'created' if table not in before else 'already exists'}")
        print(f"  columns:", [c["name"] for c in inspect(engine).get_columns(table)])
        print(f"  indexes:", [i["name"] for i in inspect(engine).get_indexes(table)])

    print("new tables:", sorted(after - before) or "none")
    print("=== init_social done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
