"""为 spots 表补齐 lat/lng 列并写入 3 个演示景点的真实坐标（v0.9）。

老版本 travel.db 没有 lat/lng 列。脚本用 SQLAlchemy inspector 检查现有列，
缺列时执行 ALTER TABLE spots ADD COLUMN ... 补齐，然后按景点名更新坐标。
脚本可重复执行：第二次运行不会新增列，只会重复写入同样的坐标。
绝不影响其他业务表，也不删除数据库文件。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import engine

# 3 个演示景点的真实经纬度（lat 纬度，lng 经度）
SPOT_COORDS = {
    "西湖景区": (30.2417, 120.1500),
    "故宫博物院": (39.9163, 116.3972),
    "外滩": (31.2397, 121.4909),
}


def column_names() -> set:
    """返回 spots 表当前所有列名。"""
    return {col["name"] for col in inspect(engine).get_columns("spots")}


def row_count() -> int:
    """返回 spots 表当前行数。"""
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM spots")).scalar() or 0


def main():
    print("=== init_spot_coords start ===")
    before = row_count()
    print("spots row count before:", before)

    existing = column_names()
    added = 0
    with engine.begin() as conn:
        if "lat" not in existing:
            conn.execute(text("ALTER TABLE spots ADD COLUMN lat FLOAT"))
            added += 1
            print("added column: lat")
        if "lng" not in existing:
            conn.execute(text("ALTER TABLE spots ADD COLUMN lng FLOAT"))
            added += 1
            print("added column: lng")

    updated = 0
    with engine.begin() as conn:
        for name, (lat, lng) in SPOT_COORDS.items():
            result = conn.execute(
                text("UPDATE spots SET lat = :lat, lng = :lng WHERE name = :name"),
                {"lat": lat, "lng": lng, "name": name},
            )
            if result.rowcount:
                updated += result.rowcount

    after = row_count()
    print("columns added:", added)
    print("coordinates written:", updated)
    print("spots row count after:", after)
    print("=== init_spot_coords done ===")


if __name__ == "__main__":
    main()
