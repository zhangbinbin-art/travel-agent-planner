"""为缺少客房的酒店补初始房型（幂等，可重复执行）。

背景：
    /api/v1/hotel/order 在未传 room_id 时会自动挑选「status=free 且 stock>0」的房间，
    若酒店没有任何房间记录，会直接返回 400「该酒店暂无可预订客房」。
    演示库里多数酒店只有酒店记录、没有房间，因此补一批基础房型。

用法：
    python scripts/init_hotel_rooms.py            # 预览
    python scripts/init_hotel_rooms.py --apply    # 写库

规则：
    - 已有房间的酒店一律跳过，不覆盖商户后台维护过的房型；
    - 房型单价按酒店单价的 0.8 / 1.0 / 1.4 倍生成，四舍五入到整数；
    - 只新增 rooms 记录，不改动酒店、订单、账单等任何业务数据。
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models import Hotel, Room

# (房型名, 单价系数, 库存)
ROOM_TEMPLATES = [
    ("标准大床房", 0.8, 10),
    ("双床房", 1.0, 8),
    ("家庭套房", 1.4, 5),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="写库（默认只预览）")
    args = parser.parse_args()

    db = SessionLocal()
    hotels = db.query(Hotel).order_by(Hotel.id).all()
    plan = []

    print("=== 酒店 %d 家 | 模式：%s ===" % (len(hotels), "APPLY" if args.apply else "DRY-RUN"))
    for hotel in hotels:
        existing = db.query(Room).filter(Room.hotel_id == hotel.id).count()
        if existing:
            print("[SKIP] id=%-3s %-24s 已有 %d 个房型" % (hotel.id, hotel.name, existing))
            continue
        base = float(hotel.price_per_day or 300)
        rooms = []
        for name, factor, stock in ROOM_TEMPLATES:
            rooms.append(
                {
                    "room_type": name,
                    "room_price": round(base * factor, 2),
                    "stock": stock,
                    "status": "free",
                }
            )
        plan.append((hotel, rooms))
        detail = ", ".join("%s ¥%s×%s" % (r["room_type"], r["room_price"], r["stock"]) for r in rooms)
        print("[FIX ] id=%-3s %-24s -> %s" % (hotel.id, hotel.name, detail))

    print("=== 需补房型 %d 家 ===" % len(plan))
    if not args.apply or not plan:
        return 0

    for hotel, rooms in plan:
        for room in rooms:
            db.add(
                Room(
                    hotel_id=hotel.id,
                    room_type=room["room_type"],
                    room_price=room["room_price"],
                    stock=room["stock"],
                    status=room["status"],
                    create_time=datetime.now(),
                )
            )
    db.commit()
    print("已为 %d 家酒店补充客房。" % len(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
