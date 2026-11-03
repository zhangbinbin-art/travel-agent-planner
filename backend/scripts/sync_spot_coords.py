"""按景点名称 + 城市回填真实经纬度（高德 POI 搜索优先，地理编码兜底）。

用法：
    python scripts/sync_spot_coords.py            # dry-run，只打印对比表
    python scripts/sync_spot_coords.py --apply    # 写库（写前自动备份旧值到 JSON）

说明：
    1. 只更新 spots.lat/lng，不新增、不删除任何记录，不影响 posts/favorites/trips 的引用；
    2. 新坐标与旧坐标偏差 < 0.1km 时跳过，避免抖动改写已正确的数据；
    3. 高德个人 Key 有 QPS 限制，脚本按 0.6s 间隔串行请求，命中 CUQPS 时退避重试；
    4. 需要 backend/.env 中配置 AMAP_WEB_KEY（Web 服务类型 Key）。
"""

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.parse
import urllib.request

from core.config import settings
from core.database import SessionLocal
from models import Spot

REQUEST_INTERVAL = 0.6      # 秒，控制 QPS
MAX_RETRY = 3
RETRY_BACKOFF = 1.5
MIN_UPDATE_KM = 0.1         # 偏差小于该值视为已正确


def _http_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=6) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_with_retry(url: str) -> dict:
    last = {}
    for attempt in range(MAX_RETRY):
        try:
            data = _http_get(url)
        except Exception as exc:
            last = {"status": "0", "info": "REQUEST_FAILED: %s" % exc}
            time.sleep(RETRY_BACKOFF * (attempt + 1))
            continue
        info = str(data.get("info") or "")
        if str(data.get("status")) == "1" and "EXCEEDED_THE_LIMIT" not in info.upper():
            return data
        last = data
        if "DAILY" in info.upper():
            # 当日额度用尽，重试无意义
            return data
        if "QPS" in info.upper() or "EXCEEDED_THE_LIMIT" in info.upper():
            time.sleep(RETRY_BACKOFF * (attempt + 1))
            continue
        return data
    return last


def _parse_location(location: str) -> Optional[Tuple[float, float]]:
    try:
        lng_text, lat_text = str(location).split(",")
        return (round(float(lng_text), 6), round(float(lat_text), 6))
    except Exception:
        return None


def search_poi(name: str, city: str) -> dict:
    """高德 POI 搜索：返回 {lng, lat, source, amap_name, address} 或 {error}。"""
    if not settings.AMAP_WEB_KEY:
        return {"error": "未配置 AMAP_WEB_KEY"}

    params = {
        "key": settings.AMAP_WEB_KEY,
        "keywords": name,
        "city": city or "",
        "citylimit": "true",
        "offset": "5",
        "page": "1",
        "extensions": "base",
    }
    data = _call_with_retry("https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params))
    if str(data.get("status")) != "1":
        return {"error": str(data.get("info") or "place/text failed")}

    pois = data.get("pois") or []
    if pois:
        # 打分：名称完全一致 > 互为子串；同时优先旅游景点类 POI（11xxxx），
        # 降权泛地名/自然地名（19xxxx）与交通设施（15xxxx），避免落到路名或行政区中心。
        def score(poi):
            poi_name = str(poi.get("name") or "")
            typecode = str(poi.get("typecode") or "")
            value = 0
            if poi_name == name:
                value += 100
            elif name in poi_name or poi_name in name:
                value += 50
            if typecode.startswith("1102"):
                value += 40          # 风景名胜 / 公园广场
            elif typecode.startswith("11"):
                value += 30          # 其他旅游景点
            elif typecode.startswith("08"):
                value += 10          # 娱乐场所（乐园类）
            if typecode.startswith("19"):
                value -= 60          # 泛 POI / 自然地名
            if typecode.startswith("15"):
                value -= 60          # 交通设施
            if typecode.startswith("07"):
                value -= 30          # 生活服务（售票处等）
            if "\u00b7" in poi_name or "-" in poi_name:
                value -= 30          # 子景点/内部设施（如“xx·桃李园”“xx-断桥残雪”）
            return -value

        pois = sorted(pois, key=score)
        best = pois[0]
        coords = _parse_location(best.get("location") or "")
        if coords:
            lng, lat = coords
            return {
                "lng": lng,
                "lat": lat,
                "source": "poi",
                "amap_name": best.get("name"),
                "address": "%s%s%s" % (
                    best.get("cityname") or "",
                    best.get("adname") or "",
                    best.get("address") or "",
                ),
            }

    # 兜底：地理编码
    params = {
        "key": settings.AMAP_WEB_KEY,
        "address": name,
        "city": city or "",
        "output": "JSON",
    }
    data = _call_with_retry("https://restapi.amap.com/v3/geocode/geo?" + urllib.parse.urlencode(params))
    if str(data.get("status")) != "1":
        return {"error": str(data.get("info") or "geocode failed")}
    geocodes = data.get("geocodes") or []
    if not geocodes:
        return {"error": "no result"}
    first = geocodes[0]
    coords = _parse_location(first.get("location") or "")
    if not coords:
        return {"error": "bad location"}
    lng, lat = coords
    return {
        "lng": lng,
        "lat": lat,
        "source": "geocode",
        "amap_name": first.get("formatted_address"),
        "address": "%s%s%s" % (
            first.get("province") or "",
            first.get("city") or "",
            first.get("district") or "",
        ),
    }


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    (lng1, lat1), (lng2, lat2) = a, b
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    h = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return round(2 * 6371 * asin(sqrt(h)), 3)


def main() -> int:
    parser = argparse.ArgumentParser(description="回填景点真实经纬度")
    parser.add_argument("--apply", action="store_true", help="写库（默认只预览）")
    parser.add_argument("--interval", type=float, default=REQUEST_INTERVAL, help="请求间隔秒数")
    args = parser.parse_args()

    if not settings.AMAP_WEB_KEY:
        print("[ERROR] 未配置 AMAP_WEB_KEY，请先在 backend/.env 填写 Web 服务 Key")
        return 2

    db = SessionLocal()
    spots = db.query(Spot).order_by(Spot.id).all()
    print("=== 待处理景点 %d 个 | 模式：%s ===" % (len(spots), "APPLY" if args.apply else "DRY-RUN"))

    backup = []
    plan = []
    failed = 0
    for idx, spot in enumerate(spots):
        if idx > 0:
            time.sleep(max(0.0, args.interval))
        result = search_poi(spot.name, spot.city or "")
        if "error" in result:
            failed += 1
            print("[FAIL] id=%-3s %-12s %-4s -> %s" % (spot.id, spot.name, spot.city, result["error"]))
            continue

        old = None
        if spot.lng is not None and spot.lat is not None:
            old = (float(spot.lng), float(spot.lat))
        new = (result["lng"], result["lat"])
        diff = haversine_km(old, new) if old else None
        skip = diff is not None and diff < MIN_UPDATE_KM

        print(
            "[%s] id=%-3s %-12s %-4s old=%-22s new=%-22s diff=%-7s %s | %s"
            % (
                "SKIP" if skip else "FIX ",
                spot.id,
                spot.name,
                spot.city,
                "%s,%s" % old if old else "None",
                "%s,%s" % new,
                ("%.3fkm" % diff) if diff is not None else "-",
                result["source"],
                result.get("amap_name") or "",
            )
        )

        if skip:
            continue
        backup.append({
            "id": spot.id,
            "name": spot.name,
            "city": spot.city,
            "old_lng": spot.lng,
            "old_lat": spot.lat,
            "new_lng": new[0],
            "new_lat": new[1],
        })
        plan.append((spot, new))

    print("=== 需更新 %d 个，已正确跳过 %d 个，获取失败 %d 个 ===" % (len(plan), len(spots) - len(plan) - failed, failed))
    if not plan:
        print("没有需要更新的景点。")
        return 0

    if not args.apply:
        print("DRY-RUN 结束，加 --apply 才会写库。")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(
        os.environ.get("TEMP", r"C:\Users\zbb\AppData\Local\Temp"),
        "opencode",
        "spot_coords_backup_%s.json" % ts,
    )
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    with io.open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    print("旧值备份：%s" % backup_path)

    for spot, (lng, lat) in plan:
        spot.lng = lng
        spot.lat = lat
    db.commit()
    print("已写入 %d 个景点的真实坐标。" % len(plan))

    db.expire_all()
    for spot, _ in plan:
        fresh = db.query(Spot).filter(Spot.id == spot.id).first()
        print("  id=%-3s %-12s -> %s,%s" % (fresh.id, fresh.name, fresh.lng, fresh.lat))
    return 0


if __name__ == "__main__":
    sys.exit(main())
