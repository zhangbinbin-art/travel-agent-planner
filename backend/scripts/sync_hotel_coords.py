"""按酒店地址回填真实经纬度（高德地理编码），供行程地图打点使用。

用法：
    python scripts/sync_hotel_coords.py            # 预览
    python scripts/sync_hotel_coords.py --apply    # 写库（写前备份旧值）

说明：
    1. 只更新 hotels.lat/lng，不新增/删除任何记录，不影响预订、支付、商户管理；
    2. 地理编码失败（地址不完整/虚构地址）的酒店保持原值，地图上不会出现该点；
    3. 与景点脚本一致：0.6s 间隔 + CUQPS 退避重试。
"""

import argparse
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import SessionLocal
from models import Hotel

MIN_UPDATE_KM = 0.1
MAX_RETRY = 3
RETRY_BACKOFF = 1.5


def _call(url: str) -> dict:
    last = {}
    for attempt in range(MAX_RETRY):
        try:
            with urllib.request.urlopen(url, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last = {"status": "0", "info": str(exc)}
            time.sleep(RETRY_BACKOFF * (attempt + 1))
            continue
        info = str(data.get("info") or "").upper()
        if str(data.get("status")) == "1" and "EXCEEDED_THE_LIMIT" not in info:
            return data
        last = data
        if "DAILY" in info.upper():
            return data
        if "QPS" in info.upper() or "EXCEEDED_THE_LIMIT" in info.upper():
            time.sleep(RETRY_BACKOFF * (attempt + 1))
            continue
        return data
    return last


def geocode(address: str) -> Optional[Tuple[float, float]]:
    if not address or not settings.AMAP_WEB_KEY:
        return None
    params = {"key": settings.AMAP_WEB_KEY, "address": address, "output": "JSON"}
    data = _call("https://restapi.amap.com/v3/geocode/geo?" + urllib.parse.urlencode(params))
    if str(data.get("status")) != "1":
        return None
    geocodes = data.get("geocodes") or []
    if not geocodes:
        return None
    location = str(geocodes[0].get("location") or "")
    try:
        lng_text, lat_text = location.split(",")
        return (round(float(lng_text), 6), round(float(lat_text), 6))
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--interval", type=float, default=1.2)
    args = parser.parse_args()

    if not settings.AMAP_WEB_KEY:
        print("[ERROR] 未配置 AMAP_WEB_KEY")
        return 2

    db = SessionLocal()
    hotels = db.query(Hotel).order_by(Hotel.id).all()
    plan = []
    backup = []
    failed = 0

    print("=== 酒店 %d 家 | 模式：%s ===" % (len(hotels), "APPLY" if args.apply else "DRY-RUN"))
    for idx, hotel in enumerate(hotels):
        if idx:
            time.sleep(max(0.0, args.interval))
        coords = geocode(hotel.address or "")
        if not coords:
            failed += 1
            print("[FAIL] id=%-3s %-24s address=%s" % (hotel.id, hotel.name, hotel.address))
            continue
        lng, lat = coords
        changed = hotel.lng is None or hotel.lat is None or abs(float(hotel.lng) - lng) > 0.0005 or abs(float(hotel.lat) - lat) > 0.0005
        print("[%s] id=%-3s %-24s %s,%s" % ("FIX " if changed else "SKIP", hotel.id, hotel.name, lng, lat))
        if not changed:
            continue
        backup.append({"id": hotel.id, "name": hotel.name, "old_lng": hotel.lng, "old_lat": hotel.lat,
                       "new_lng": lng, "new_lat": lat})
        plan.append((hotel, lng, lat))

    print("=== 需更新 %d 家，失败 %d 家 ===" % (len(plan), failed))
    if not args.apply or not plan:
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(os.environ.get("TEMP", "/tmp"), "opencode", "hotel_coords_backup_%s.json" % ts)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    with io.open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    print("旧值备份：%s" % backup_path)

    for hotel, lng, lat in plan:
        hotel.lng = lng
        hotel.lat = lat
    db.commit()
    print("已写入 %d 家酒店的真实坐标。" % len(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
