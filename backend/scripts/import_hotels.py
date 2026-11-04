"""批量补充酒店数据：广州 ≥34 家，其余有景点的城市各约 5 家。

用法：
    python scripts/import_hotels.py            # 预览
    python scripts/import_hotels.py --apply    # 写库

说明：
    - 酒店信息取自高德 POI 搜索（keywords=酒店，city=目标城市，citylimit=true），
      名称/地址/经纬度/首图都来自真实 POI；
    - 地址统一补上城市名，保证 /trip/smart-recommend 按 address.contains(城市) 能匹配；
    - 每家酒店自动生成 3 个基础房型（标准大床房 / 双床房 / 家庭套房），可直接下单；
    - 幂等：同名 + 同城酒店已存在则跳过；重复运行不会重复插入。
"""

import argparse
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
from models import Hotel, Room, Spot

GUANGZHOU_COUNT = 34
OTHER_CITY_COUNT = 5
REQUEST_INTERVAL = 0.6
FACILITY_POOL = ["免费停车", "早餐", "健身房", "洗衣服务", "江景房", "茶室", "露台", "接送", "会议室", "烧烤"]
ROOM_TEMPLATES = [("标准大床房", 0.8, 10), ("双床房", 1.0, 8), ("家庭套房", 1.4, 5)]


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


def search_hotels(city: str, pages: int = 1) -> list:
    key = (settings.AMAP_WEB_KEY or "").strip()
    if not key:
        return []
    results = []
    tokens = ["酒店", "宾馆"]
    for page in range(1, pages + 1):
        keyword = tokens[(page - 1) % len(tokens)]
        params = {
            "key": key,
            "keywords": keyword,
            "city": city,
            "citylimit": "true",
            "offset": "25",
            "page": str(page),
            "extensions": "all",
        }
        data = _get("https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params))
        for poi in (data.get("pois") or []):
            location = str(poi.get("location") or "")
            if "," not in location:
                continue
            # citylimit 不保证严格，这里再用 cityname 二次校验，避免跨城重复
            cityname = str(poi.get("cityname") or "")
            if cityname and city not in cityname and cityname not in city:
                continue
            name = str(poi.get("name") or "").strip()
            if not name:
                continue
            lng, lat = location.split(",")
            photos = []
            for photo in poi.get("photos") or []:
                url = str(photo.get("url") or "").strip()
                if url.startswith("http://"):
                    url = "https://" + url[len("http://"):]
                if url and url not in photos:
                    photos.append(url)
            results.append(
                {
                    "name": name,
                    "address": str(poi.get("address") or "") or city,
                    "lng": float(lng),
                    "lat": float(lat),
                    "cover": photos[0] if photos else None,
                }
            )
        time.sleep(REQUEST_INTERVAL)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not (settings.AMAP_WEB_KEY or "").strip():
        print("[ERROR] 未配置 AMAP_WEB_KEY")
        return 2

    db = SessionLocal()
    cities = []
    for (city,) in db.query(Spot.city).distinct().all():
        if city and city.strip():
            cities.append(city.strip())
    # 广州优先并放在最前
    cities = ["广州"] + [c for c in cities if c != "广州"]

    rng = random.Random(20261104)
    total_created = 0
    total_skipped = 0
    report = []

    for city in cities:
        target = GUANGZHOU_COUNT if city == "广州" else OTHER_CITY_COUNT
        existing_names = {
            str(h.name or "").strip()
            for h in db.query(Hotel).filter(Hotel.address.contains(city)).all()
        }
        global_names = {str(h.name or "").strip() for h in db.query(Hotel).all()}
        need = target - len(existing_names)
        if need <= 0:
            report.append((city, len(existing_names), 0))
            continue

        pages = 2 if target > 25 else 1
        pois = search_hotels(city, pages=pages)
        created_here = 0
        for poi in pois:
            if created_here >= need:
                break
            name = poi["name"]
            if name in existing_names or name in global_names:
                total_skipped += 1
                continue
            address = poi["address"]
            if city not in address:
                address = "%s%s" % (city, address)
            price = rng.choice([188, 228, 268, 298, 328, 358, 398, 468, 528, 688, 888])
            hotel = Hotel(
                name=name,
                address=address,
                lng=poi["lng"],
                lat=poi["lat"],
                price_per_day=price,
                cover_img=poi["cover"],
                description="%s，位于%s，交通便利，适合商旅与休闲入住。" % (name, address),
                facilities=",".join(rng.sample(FACILITY_POOL, rng.randint(3, 6))),
                env_score=round(rng.uniform(4.0, 4.9), 1),
                service_score=round(rng.uniform(4.0, 4.9), 1),
                status="on_shelf",
            )
            print("[%s] %-30s ¥%-4s %s" % (city, name, price, address[:24]))
            if args.apply:
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
            existing_names.add(name)
            global_names.add(name)
            created_here += 1
        # POI 搜不到足量时，用该城市景点坐标均值生成演示酒店兜底
        if created_here < need:
            spots = [s for s in db.query(Spot).filter(Spot.city == city).all() if s.lat and s.lng]
            if spots:
                base_lat = sum(float(s.lat) for s in spots) / len(spots)
                base_lng = sum(float(s.lng) for s in spots) / len(spots)
                suffixes = ["中央", "滨江", "老城", "新城", "花园", "文化"]
                index = 0
                while created_here < need:
                    name = "%s%s精选酒店" % (city, suffixes[index % len(suffixes)])
                    if index >= len(suffixes):
                        name = "%s精选酒店%d" % (city, index)
                    index += 1
                    if name in global_names:
                        continue
                    lat = round(base_lat + rng.uniform(-0.02, 0.02), 6)
                    lng = round(base_lng + rng.uniform(-0.02, 0.02), 6)
                    price = rng.choice([188, 228, 268, 298, 328, 358])
                    hotel = Hotel(
                        name=name,
                        address="%s市中心区域" % city,
                        lng=lng,
                        lat=lat,
                        price_per_day=price,
                        cover_img=None,
                        description="%s，位于%s市中心，交通便利，适合商旅与休闲入住。" % (name, city),
                        facilities=",".join(rng.sample(FACILITY_POOL, 4)),
                        env_score=round(rng.uniform(4.0, 4.7), 1),
                        service_score=round(rng.uniform(4.0, 4.7), 1),
                        status="on_shelf",
                    )
                    print("[%s] %-26s ¥%-4s（坐标兜底）" % (city, name, price))
                    if args.apply:
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
                    global_names.add(name)
                    existing_names.add(name)
                    created_here += 1

        if args.apply:
            db.commit()
        total_created += created_here
        report.append((city, len(existing_names), created_here))

    print("\n=== 统计 ===")
    for city, existing, created in report:
        print("  %-6s 原有 %-3d 新增 %d" % (city, existing - created, created))
    print("合计新增酒店：%d 家 | 跳过重名：%d 家" % (total_created, total_skipped))
    if not args.apply:
        print("DRY-RUN 结束，加 --apply 才会写库。")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
