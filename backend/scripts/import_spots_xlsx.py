"""批量导入《全国旅游景点数据.xlsx》到 spots 表。

用法：
    python scripts/import_spots_xlsx.py                 # 预览（只解析校验，不写库）
    python scripts/import_spots_xlsx.py --apply         # 写库
    python scripts/import_spots_xlsx.py --file 路径.xlsx # 指定文件

规则：
    - 标签必须全部属于固定集合，出现非法标签则整条跳过并记录日志；
    - 景点名称重复（库内已存在 / 本次已导入）跳过；
    - 票价/评分/热度/经纬度转数值，经纬度非法则置空但保留记录；
    - 不写封面图，cover 留空，后续由管理员上传；
    - 复用 services.spot_service.create_spot，不新增/改动其它业务逻辑。
"""

import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models import Spot
from services import spot_service

ALLOWED_TAGS = {
    "自然风光",
    "人文古迹",
    "美食探店",
    "游乐乐园",
    "城市逛街",
    "徒步登山",
    "海滨海岛",
    "亲子出游",
}

# 标签 -> 主题（沿用库内既有 theme 口径，保证打分/筛选兼容）
TAG_THEME = {
    "自然风光": "自然风景",
    "海滨海岛": "自然风景",
    "徒步登山": "自然风景",
    "人文古迹": "历史古迹",
    "游乐乐园": "主题乐园",
    "亲子出游": "主题乐园",
    "城市逛街": "城市观光",
    "美食探店": "城市观光",
}

DEFAULT_XLSX = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "全国旅游景点数据.xlsx",
)


def _split_tags(raw) -> list:
    text = str(raw or "").replace("，", ",").replace("、", ",").replace(";", ",").replace("；", ",")
    return [t.strip() for t in text.split(",") if t.strip()]


def _to_float(value):
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    num = _to_float(value)
    return int(num) if num is not None else None


def parse_rows(path: str) -> list:
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["景点数据"] if "景点数据" in wb.sheetnames else wb[wb.sheetnames[0]]
    records = []
    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not any(row):
            continue
        province, city, name, address, tags_raw, price, score, heat, lng, lat, intro = (
            list(row) + [None] * 11
        )[:11]
        records.append(
            {
                "row": idx,
                "province": str(province or "").strip() or None,
                "city": str(city or "").strip() or None,
                "name": str(name or "").strip(),
                "address": str(address or "").strip() or None,
                "tags_raw": tags_raw,
                "tags": _split_tags(tags_raw),
                "price": _to_float(price),
                "score": _to_float(score),
                "heat": _to_int(heat),
                "lng": _to_float(lng),
                "lat": _to_float(lat),
                "intro": str(intro or "").strip() or None,
            }
        )
    return records


def validate(record: dict) -> str:
    """返回错误原因，None 表示通过。"""
    if not record["name"]:
        return "景点名称为空"
    invalid = [t for t in record["tags"] if t not in ALLOWED_TAGS]
    if invalid:
        return "非法标签: " + ",".join(invalid)
    lng, lat = record["lng"], record["lat"]
    if lng is not None and not (-180 <= lng <= 180):
        record["lng"] = None
    if lat is not None and not (-90 <= lat <= 90):
        record["lat"] = None
    return None


def build_payload(record: dict) -> dict:
    tags = record["tags"]
    theme = TAG_THEME.get(tags[0], "自然风景") if tags else None
    return {
        "name": record["name"],
        "city": record["city"],
        "province": record["province"],
        "theme": theme,
        "tags": ",".join(tags),
        "description": record["intro"],
        "score": record["score"] if record["score"] is not None else 0,
        "price": record["price"] if record["price"] is not None else 0,
        "cover": None,
        "address": record["address"],
        "heat": record["heat"] if record["heat"] is not None else 0,
        "lng": record["lng"],
        "lat": record["lat"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=DEFAULT_XLSX)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print("[ERROR] 文件不存在:", args.file)
        return 2

    records = parse_rows(args.file)
    print("=== 解析到 %d 条记录 | 模式：%s ===" % (len(records), "APPLY" if args.apply else "DRY-RUN"))

    db = SessionLocal()
    existing_names = {str(s.name or "").strip().lower() for s in db.query(Spot).all()}
    imported_names = set()

    success = 0
    dup_skipped = 0
    invalid_skipped = 0
    tag_counter = Counter()

    for record in records:
        error = validate(record)
        if error:
            invalid_skipped += 1
            print("[SKIP-非法] row=%-3s %-14s %s" % (record["row"], record["name"], error))
            continue
        key = record["name"].lower()
        if key in existing_names or key in imported_names:
            dup_skipped += 1
            print("[SKIP-重复] row=%-3s %s" % (record["row"], record["name"]))
            continue

        payload = build_payload(record)
        if args.apply:
            spot_service.create_spot(db, payload)
        imported_names.add(key)
        success += 1
        tag_counter.update(record["tags"])

    print("\n=== 导入统计 ===")
    print("成功导入：%d 条" % success)
    print("跳过重复：%d 条" % dup_skipped)
    print("非法标签丢弃：%d 条" % invalid_skipped)
    print("标签分布：", dict(tag_counter))
    if not args.apply:
        print("\nDRY-RUN 结束，加 --apply 才会写库。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
