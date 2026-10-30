"""v0.11 商户/客房/订单/实名迁移（幂等）。

- users 增加实名字段与 merchant_hotel_id
- 创建 rooms / hotel_orders / guest_records / bills
- 将商家账号绑定到唯一酒店，并补默认客房

用法：python scripts/init_v011.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import Base, SessionLocal, engine
from models import Bill, GuestRecord, Hotel, HotelOrder, Room, User


def ensure_user_columns():
    insp = inspect(engine)
    existing = {col["name"] for col in insp.get_columns("users")}
    ddl = {
        "is_real_name_auth": "BOOLEAN NOT NULL DEFAULT 0",
        "real_name": "VARCHAR(50) NULL",
        "id_card": "VARCHAR(30) NULL",
        "merchant_hotel_id": "INT NULL",
    }
    with engine.begin() as conn:
        for name, typ in ddl.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {typ}"))
                print(f"users.{name} added")


def ensure_hotel_nullable():
    """管理员可先建酒店后绑定商户，merchant_id 允许为空。"""
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("ALTER TABLE hotels MODIFY merchant_id INT NULL"))
            print("hotels.merchant_id nullable")
    except Exception as exc:
        print("skip merchant_id alter:", exc)


def ensure_tables():
    Base.metadata.create_all(
        bind=engine,
        tables=[Room.__table__, HotelOrder.__table__, GuestRecord.__table__, Bill.__table__],
        checkfirst=True,
    )
    insp = inspect(engine)
    for table in (Room.__tablename__, HotelOrder.__tablename__, GuestRecord.__tablename__, Bill.__tablename__):
        print(f"{table}:", "exists" if insp.has_table(table) else "missing")


def bind_merchants_and_rooms():
    db = SessionLocal()
    try:
        hotels = db.query(Hotel).order_by(Hotel.id.asc()).all()
        if not hotels:
            print("no hotels, skip binding")
            return
        preferred_map = {"shop01": "星期八", "shop02": "西瓜"}
        merchants = db.query(User).filter(User.role == "merchant").order_by(User.id.asc()).all()
        for idx, merchant in enumerate(merchants):
            preferred = preferred_map.get(merchant.username)
            hotel = None
            if preferred:
                hotel = next((h for h in hotels if preferred in (h.name or "")), None)
            if hotel is None:
                hotel = hotels[idx % len(hotels)]
            if getattr(merchant, "merchant_hotel_id", None) != hotel.id:
                merchant.merchant_hotel_id = hotel.id
                print(f"bind {merchant.username} -> hotel {hotel.id} {hotel.name}")
        db.commit()

        for merchant in merchants:
            hid = merchant.merchant_hotel_id
            if not hid:
                continue
            exists = db.query(Room).filter(Room.hotel_id == hid).count()
            if exists:
                continue
            samples = [
                {"room_type": "标准大床房", "room_price": 268, "bed_info": "1.8m大床", "max_guest": 2, "stock": 10},
                {"room_type": "双床房", "room_price": 328, "bed_info": "1.2m双床", "max_guest": 2, "stock": 8},
                {"room_type": "家庭套房", "room_price": 468, "bed_info": "1.8m大床+1.2m单床", "max_guest": 4, "stock": 5},
            ]
            for s in samples:
                db.add(Room(hotel_id=hid, status="free", **s))
            print(f"rooms seeded for hotel {hid}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    print("=== init_v011 start ===")
    ensure_user_columns()
    ensure_hotel_nullable()
    ensure_tables()
    bind_merchants_and_rooms()
    print("=== init_v011 done ===")
