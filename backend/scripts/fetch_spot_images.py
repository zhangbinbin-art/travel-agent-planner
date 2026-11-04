"""为景点抓取实景图（高德 POI 相册），写入 spots.images 并同步封面。

用法：
    python scripts/fetch_spot_images.py                # 预览（只查询，不写库）
    python scripts/fetch_spot_images.py --apply        # 写库
    python scripts/fetch_spot_images.py --apply --refresh   # 已有多图的也重新抓
    python scripts/fetch_spot_images.py --apply --limit 50  # 只处理前 50 个

说明：
    - 图片来自高德 POI 相册（extensions=all），每景点取最多 3 张；
    - 幂等：默认跳过已有 ≥2 张图的景点；
    - 只更新 spots.images / spots.cover，不动其它字段与业务逻辑。
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import SessionLocal
from models import Spot

MAX_PHOTOS = 3
REQUEST_INTERVAL = 0.45
MAX_RETRY = 3


def _get(url: str) -> dict:
    last = {}
    for attempt in range(MAX_RETRY):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            info = str(data.get("info") or "").upper()
            if str(data.get("status")) == "1" and "EXCEEDED_THE_LIMIT" not in info:
                return data
            last = data
            if "QPS" in info or "EXCEEDED_THE_LIMIT" in info:
                time.sleep(1.2 * (attempt + 1))
                continue
            return data
        except Exception as exc:
            last = {"status": "0", "info": str(exc)}
            time.sleep(1.2 * (attempt + 1))
    return last


def _normalize(url: str) -> str:
    url = str(url or "").strip()
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


def fetch_photos(name: str, city: str) -> list:
    key = (settings.AMAP_WEB_KEY or "").strip()
    if not key:
        return []
    params = {
        "key": key,
        "keywords": name,
        "city": city or "",
        "citylimit": "true",
        "offset": "5",
        "page": "1",
        "extensions": "all",
    }
    data = _get("https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params))
    if str(data.get("status")) != "1":
        return []

    photos = []
    seen = set()
    for poi in data.get("pois") or []:
        for photo in poi.get("photos") or []:
            url = _normalize(photo.get("url"))
            if not url or url in seen:
                continue
            seen.add(url)
            photos.append(url)
            if len(photos) >= MAX_PHOTOS:
                return photos
    return photos


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not (settings.AMAP_WEB_KEY or "").strip():
        print("[ERROR] 未配置 AMAP_WEB_KEY")
        return 2

    db = SessionLocal()
    query = db.query(Spot).order_by(Spot.id.asc())
    if args.limit:
        query = query.limit(args.limit)
    spots = query.all()
    print("=== 待处理景点 %d 个 | 模式：%s ===" % (len(spots), "APPLY" if args.apply else "DRY-RUN"))

    updated = 0
    skipped = 0
    failed = 0
    total_photos = 0

    for idx, spot in enumerate(spots):
        existing = []
        try:
            existing = json.loads(spot.images) if spot.images else []
        except Exception:
            existing = []
        if len(existing) >= 2 and not args.refresh:
            skipped += 1
            continue
        if idx:
            time.sleep(REQUEST_INTERVAL)

        photos = fetch_photos(spot.name, spot.city or "")
        if not photos:
            failed += 1
            print("[MISS] id=%-4s %-20s %s" % (spot.id, spot.name, spot.city))
            continue

        total_photos += len(photos)
        print("[OK  ] id=%-4s %-20s %d 张" % (spot.id, spot.name, len(photos)))
        if args.apply:
            spot.images = json.dumps(photos, ensure_ascii=False)
            if photos:
                spot.cover = photos[0]
        updated += 1

    if args.apply:
        db.commit()

    print("\n=== 统计 ===")
    print("更新景点：%d 个 | 已有图跳过：%d 个 | 未找到图片：%d 个" % (updated, skipped, failed))
    if updated:
        print("平均每个景点 %d 张图" % round(total_photos / updated, 1))
    if not args.apply:
        print("DRY-RUN 结束，加 --apply 才会写库。")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
