"""再为广州补充 30 家酒店（在现有基础上）。"""

import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import SessionLocal
from models import Hotel, Room

CITY = "广州"
TARGET_EXTRA = 30
FACILITY_POOL = ["免费停车", "早餐", "健身房", "洗衣服务", "江景房", "茶室", "露台", "接送", "会议室", "烧烤"]
ROOM_TEMPLATES = [("标准大床房", 0.8, 10), ("双床房", 1.0, 8), ("家庭套房", 1.4, 5)]
KEYWORDS = ["酒店", "宾馆", "民宿", "公寓", "国际酒店"]


def _get(url: str) -> dict:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            info = str(data.get("info") or "").upper()
            if str(data.get("status")) == "1" and "EXCEEDED_THE_LIMIT" not in info:
                return data
            if "QPS" in info or "EXCEEDED_THE_LIMIT" in info:
                time.sleep(1.2 * (attempt + 1))
                continue
            return data
        except Exception:
            time.sleep(1.0 * (attempt + 1))
    return {}


def search_page(keyword: str, page: int) -> list:
    key = (settings.AMAP_WEB_KEY or "").strip()
    params = {
        "key": key,
        "keywords": keyword,
        "city": CITY,
        "citylimit": "true",
        "offset": "25",
        "page": str(page),
        "extensions": "all",
    }
    data = _get("https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params))
    out = []
    for poi in data.get("pois") or []:
        cityname = str(poi.get("cityname") or "")
        if cityname and CITY not in cityname and cityname not in CITY:
            continue
        location = str(poi.get("location") or "")
        name = str(poi.get("name") or "").strip()
        if "," not in location or not name:
            continue
        lng, lat = location.split(",")
        photos = []
        for photo in poi.get("photos") or []:
            url = str(photo.get("url") or "").strip()
            if url.startswith("http://"):
                url = "https://" + url[len("http://"):]
            if url and url not in photos:
                photos.append(url)
        address = str(poi.get("address") or "") or CITY
        if CITY not in address:
            address = CITY + address
        out.append({"name": name, "address": address, "lng": float(lng), "lat": float(lat), "cover": photos[0] if photos else None})
    return out


def main() -> int:
    apply = "--apply" in sys.argv
    db = SessionLocal()
    existing = {str(h.name or "").strip() for h in db.query(Hotel).all()}
    current = db.query(Hotel).filter(Hotel.address.contains(CITY)).count()
    need = TARGET_EXTRA
    print("=== 广州现有 %d 家，计划新增 %d 家 | %s ===" % (current, need, "APPLY" if apply else "DRY-RUN"))

    rng = random.Random(20261105)
    created = 0
    for keyword in KEYWORDS:
        for page in (1, 2, 3):
            if created >= need:
                break
            for poi in search_page(keyword, page):
                if created >= need:
                    break
                if poi["name"] in existing:
                    continue
                price = rng.choice([168, 198, 228, 268, 298, 328, 368, 428, 528, 688])
                print("[OK] %-32s ¥%-4s %s" % (poi["name"][:30], price, poi["address"][:22]))
                if apply:
                    hotel = Hotel(
                        name=poi["name"],
                        address=poi["address"],
                        lng=poi["lng"],
                        lat=poi["lat"],
                        price_per_day=price,
                        cover_img=poi["cover"],
                        description="%s，位于%s市中心，交通便利，适合商旅与休闲入住。" % (poi["name"], CITY),
                        facilities=",".join(rng.sample(FACILITY_POOL, rng.randint(3, 6))),
                        env_score=round(rng.uniform(4.1, 4.9), 1),
                        service_score=round(rng.uniform(4.1, 4.9), 1),
                        status="on_shelf",
                    )
                    db.add(hotel)
                    db.flush()
                    for room_type, factor, stock in ROOM_TEMPLATES:
                        db.add(
                            Room(
                                hotel_id=hotel.id,
                                room_type=room_type,
                                room_price=round(price * factor, 2),
                                stock=stock,
                                status="free",
                            )
                        )
                existing.add(poi["name"])
                created += 1
            time.sleep(0.5)

    if apply:
        db.commit()
    print("\n=== 新增 %d 家 | 广州当前 %d 家 ===" % (
        created, db.query(Hotel).filter(Hotel.address.contains(CITY)).count() if apply else current + created))
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
