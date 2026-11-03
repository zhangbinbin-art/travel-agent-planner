"""初始化酒店资料/资质审核表，并为历史酒店补“已通过”记录。

用法：
    python scripts/migrate_hotel_audit.py            # 预览
    python scripts/migrate_hotel_audit.py --apply    # 执行

说明：
    - 创建 hotel_profiles / hotel_certifications 两张表；
    - hotels 表补 phone / imgs / checkin_rule 列；
    - 历史酒店（已绑定商户）补写一条 approved 资料 + approved 资质，
      保证客户端原有酒店不被下架；新商户进入后默认是空资料，需要自行提交审核。
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import Base, SessionLocal, engine
from models import Hotel, HotelCertification, HotelProfile

DEFAULT_RULE = "入住 14:00 后，退房 12:00 前"


def add_hotel_columns(apply: bool) -> None:
    columns = {col["name"] for col in inspect(engine).get_columns("hotels")}
    wanted = {
        "phone": "VARCHAR(30) NULL",
        "imgs": "TEXT NULL",
        "checkin_rule": "VARCHAR(255) NULL",
    }
    for name, ddl in wanted.items():
        if name in columns:
            continue
        print("[FIX ] hotels.%s 缺失" % name)
        if apply:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE hotels ADD COLUMN %s %s" % (name, ddl)))
            print("[DONE] 已添加 hotels.%s" % name)


def backfill(apply: bool) -> None:
    db = SessionLocal()
    hotels = db.query(Hotel).filter(Hotel.merchant_id.isnot(None)).all()
    done_shops = set()
    for hotel in hotels:
        shop_id = hotel.merchant_id
        # 同一商户可能挂了多家历史酒店，只补一条资料/认证
        if shop_id in done_shops:
            continue
        done_shops.add(shop_id)
        profile = db.query(HotelProfile).filter(HotelProfile.shop_id == shop_id).first()
        cert = db.query(HotelCertification).filter(HotelCertification.shop_id == shop_id).first()
        need_profile = profile is None
        need_cert = cert is None
        if not need_profile and not need_cert:
            continue
        print("[BACKFILL] shop=%-3s hotel=%-20s profile=%s cert=%s" % (shop_id, hotel.name, need_profile, need_cert))
        if not apply:
            continue
        if need_profile:
            db.add(
                HotelProfile(
                    shop_id=shop_id,
                    name=hotel.name,
                    address=hotel.address,
                    lng=None if hotel.lng is None else str(hotel.lng),
                    lat=None if hotel.lat is None else str(hotel.lat),
                    phone=None,
                    intro=hotel.description,
                    imgs=json.dumps([hotel.cover_img] if hotel.cover_img else [], ensure_ascii=False),
                    tags=json.dumps([t for t in (hotel.facilities or "").split(",") if t], ensure_ascii=False),
                    checkin_rule=DEFAULT_RULE,
                    status="approved",
                    submit_time=datetime.now(),
                    audit_time=datetime.now(),
                )
            )
        if need_cert:
            db.add(
                HotelCertification(
                    shop_id=shop_id,
                    hotel_full_name=hotel.name,
                    credit_code="LEGACY%06d" % shop_id,
                    legal_name="历史商户",
                    legal_phone=None,
                    license_img=None,
                    id_card_imgs="[]",
                    status="approved",
                    submit_time=datetime.now(),
                    audit_time=datetime.now(),
                )
            )
    if apply:
        db.commit()
    db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print("=== 建表（hotel_profiles / hotel_certifications）===")
    if args.apply:
        Base.metadata.create_all(bind=engine)
        print("[DONE] 表已就绪")
    add_hotel_columns(args.apply)
    backfill(args.apply)
    if not args.apply:
        print("DRY-RUN 结束，加 --apply 才会执行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
