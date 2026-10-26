import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect

import models  # noqa: F401  注册所有模型到 Base.metadata
from core.database import Base, engine

EXPECTED_COLUMNS = {
    "id",
    "user_id",
    "name",
    "route_json",
    "total_distance",
    "created_at",
}


def main():
    inspector = inspect(engine)

    if inspector.has_table("trips"):
        existing = {column["name"] for column in inspector.get_columns("trips")}
        if existing == EXPECTED_COLUMNS:
            print("trips table exists with expected columns - no change")
        else:
            print("trips table schema mismatch - dropping old empty table")
            print("  found:   " + ", ".join(sorted(existing)))
            print("  expected:" + ", ".join(sorted(EXPECTED_COLUMNS)))
            models.Trip.__table__.drop(bind=engine, checkfirst=True)
    else:
        print("trips table missing - will create")

    # 只创建缺失的表；已存在且结构正确的表不会被改动
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    final_columns = {column["name"] for column in inspector.get_columns("trips")}
    if final_columns != EXPECTED_COLUMNS:
        print("ERROR: trips table columns still do not match")
        print("  final: " + ", ".join(sorted(final_columns)))
        sys.exit(1)

    print("trips table ready: " + ", ".join(sorted(final_columns)))


if __name__ == "__main__":
    main()
