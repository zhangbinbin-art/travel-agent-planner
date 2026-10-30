"""酒店商家模块初始化脚本（幂等）。

作用：
1. 为 users 表补充 audit_status 列（存在则跳过），普通/管理员默认 approved；
2. 创建 hotels / hotel_bookings 表（不存在时创建，不动其他表）；
3. 将已有商家账号标记为 approved，便于演示。

用法：python scripts/init_hotel.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import Base, SessionLocal, engine
from models import Hotel, HotelBooking, User


def ensure_user_audit_column():
    insp = inspect(engine)
    columns = {col["name"] for col in insp.get_columns("users")}
    if "audit_status" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN audit_status VARCHAR(20) "
                    "NOT NULL DEFAULT 'approved'"
                )
            )
        print("users.audit_status added")
    else:
        print("users.audit_status exists")


def _add_missing_columns(table_name: str, ddl: dict):
    insp = inspect(engine)
    existing = {col["name"] for col in insp.get_columns(table_name)}
    with engine.begin() as conn:
        for name, typ in ddl.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {typ}"))
                print(f"{table_name}.{name} added")


def ensure_tables():
    Base.metadata.create_all(
        bind=engine, tables=[Hotel.__table__, HotelBooking.__table__], checkfirst=True
    )
    insp = inspect(engine)
    for table in (Hotel.__tablename__, HotelBooking.__tablename__):
        print(f"{table}:", "exists" if insp.has_table(table) else "missing")

    # 兼容旧库：补充评分/配套/预约扩展字段
    _add_missing_columns(
        Hotel.__tablename__,
        {
            "facilities": "TEXT NULL",
            "env_score": "FLOAT NULL DEFAULT 0",
            "service_score": "FLOAT NULL DEFAULT 0",
        },
    )
    _add_missing_columns(
        HotelBooking.__tablename__,
        {
            "guest_count": "INT NULL DEFAULT 1",
            "remark": "VARCHAR(500) NULL",
            "route_id": "INT NULL",
        },
    )


def approve_merchants():
    db = SessionLocal()
    try:
        # 仅修复历史数据里 audit_status 为空的老商家；不改变已存在的审核状态
        merchants = db.query(User).filter(User.role == "merchant").all()
        for m in merchants:
            if getattr(m, "audit_status", None) is None:
                m.audit_status = "approved"
                print(f"merchant audit_status filled: {m.username}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    print("=== init_hotel start ===")
    ensure_user_audit_column()
    ensure_tables()
    approve_merchants()
    print("=== init_hotel done ===")
