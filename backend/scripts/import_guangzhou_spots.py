"""补充广州景点数据（约 40 条），字段与现有景点一致，含高德坐标与 3 张实景图。

用法：
    python scripts/import_guangzhou_spots.py            # 预览
    python scripts/import_guangzhou_spots.py --apply    # 写库

说明：
    - 名称按库内已有记录判重，重复运行不会重复插入；
    - 地址/经纬度/相册取自高德 POI 搜索（city=广州，citylimit=true）；
    - 标签只使用 8 个固定标签，theme 按标签映射到库内既有口径；
    - 图片写入 spots.images，首图同步为 cover。
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
from services import spot_service

CITY = "广州"
PROVINCE = "广东"
MAX_PHOTOS = 3
INTERVAL = 0.5

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

# (名称, 标签, 票价, 评分, 热度, 简介)
SPOTS = [
    ("广州塔", ["城市逛街"], 150, 4.8, 98, "广州地标“小蛮腰”，可在顶层观景台俯瞰珠江与城市天际线。"),
    ("沙面岛", ["人文古迹", "城市逛街"], 0, 4.7, 92, "欧陆风情建筑群聚集的江心小岛，适合散步与拍照。"),
    ("陈家祠", ["人文古迹"], 10, 4.8, 95, "岭南传统建筑艺术代表，木雕、砖雕、灰塑工艺精美。"),
    ("上下九步行街", ["城市逛街", "美食探店"], 0, 4.5, 90, "老广州商业街区，骑楼建筑与地道小吃集中。"),
    ("北京路步行街", ["城市逛街", "美食探店"], 0, 4.6, 93, "千年古道遗址与现代商业结合的步行街，夜间人气旺。"),
    ("越秀公园", ["自然风光", "人文古迹"], 0, 4.6, 88, "广州老牌城市公园，五羊石像与镇海楼都在附近。"),
    ("中山纪念堂", ["人文古迹"], 10, 4.7, 87, "纪念孙中山先生的八角形建筑，木棉花季尤其好看。"),
    ("黄埔军校旧址", ["人文古迹"], 0, 4.7, 86, "近代军事院校旧址，展陈还原了当年的学习生活场景。"),
    ("南越王博物院", ["人文古迹"], 12, 4.8, 84, "西汉南越国墓室原址博物馆，出土文物极具岭南特色。"),
    ("广东省博物馆", ["人文古迹", "亲子出游"], 0, 4.8, 91, "免费开放的综合博物馆，自然与历史展厅适合亲子。"),
    ("海心沙", ["城市逛街"], 0, 4.5, 85, "珠江边的开放广场，夜晚可看广州塔灯光与江景。"),
    ("花城广场", ["城市逛街"], 0, 4.6, 89, "珠江新城中轴线广场，周边大剧院、图书馆环绕。"),
    ("广州大剧院", ["城市逛街"], 0, 4.6, 80, "扎哈·哈迪德设计的“圆润双砾”，建筑本身即是看点。"),
    ("石室圣心大教堂", ["人文古迹"], 0, 4.7, 83, "全花岗岩建造的哥特式教堂，彩窗与尖顶十分出片。"),
    ("光孝寺", ["人文古迹"], 5, 4.6, 78, "岭南著名古刹，历史可追溯至东晋，环境清幽。"),
    ("六榕寺", ["人文古迹"], 5, 4.5, 76, "以花塔闻名的古寺，苏东坡题字“六榕”留存至今。"),
    ("荔湾湖公园", ["自然风光"], 0, 4.5, 74, "西关风情园林，湖面开阔，适合慢走与早茶后散步。"),
    ("流花湖公园", ["自然风光"], 0, 4.4, 72, "市区内的大片湖景绿地，清晨跑步的人不少。"),
    ("天河公园", ["自然风光"], 0, 4.3, 70, "天河区大型综合公园，树荫多，适合日常休闲。"),
    ("华南植物园", ["自然风光", "亲子出游"], 20, 4.7, 82, "国内大型植物园之一，温室与棕榈园区值得细逛。"),
    ("广州动物园", ["亲子出游"], 20, 4.4, 81, "老牌城市动物园，动物种类多，适合带孩子。"),
    ("广州海洋馆", ["亲子出游"], 130, 4.3, 75, "位于动物园内的海洋馆，有海豚与海底隧道。"),
    ("岭南印象园", ["人文古迹", "亲子出游"], 60, 4.4, 73, "复原岭南传统村落风貌，民俗表演与手作体验丰富。"),
    ("宝墨园", ["人文古迹"], 54, 4.6, 71, "番禺园林式景区，砖雕与锦鲤池是主要看点。"),
    ("余荫山房", ["人文古迹"], 18, 4.6, 69, "广东四大名园之一，小巧精致，布局讲究。"),
    ("莲花山旅游区", ["自然风光", "人文古迹"], 54, 4.6, 77, "古采石场遗址与望海观音像，登高可望狮子洋。"),
    ("大夫山森林公园", ["自然风光", "徒步登山"], 0, 4.5, 79, "番禺大型森林公园，绿道骑行与徒步都合适。"),
    ("南沙天后宫", ["人文古迹"], 20, 4.5, 68, "面向珠江口的妈祖庙，登塔可看海景。"),
    ("南沙湿地公园", ["自然风光", "海滨海岛"], 30, 4.4, 66, "珠江口湿地，冬季候鸟多，适合观鸟与骑行。"),
    ("白水寨风景名胜区", ["自然风光", "徒步登山"], 60, 4.7, 85, "增城白水寨瀑布落差大，登山栈道一路溪水相伴。"),
    ("从化温泉", ["自然风光"], 100, 4.4, 64, "从化温泉度假区，适合安排一晚放松行程。"),
    ("溪头村", ["自然风光", "徒步登山"], 0, 4.3, 62, "从化山村，竹林与溪流环绕，适合轻徒步。"),
    ("广州起义烈士陵园", ["人文古迹"], 0, 4.5, 60, "纪念广州起义的陵园，环境庄重，绿化很好。"),
    ("农民运动讲习所旧址", ["人文古迹"], 0, 4.5, 58, "毛泽东同志主办的农讲所旧址，红墙建筑很上镜。"),
    ("广州博物馆", ["人文古迹"], 10, 4.5, 63, "馆址镇海楼，登楼可俯瞰越秀山与老城区。"),
    ("永庆坊", ["人文古迹", "城市逛街"], 0, 4.6, 88, "西关旧城改造街区，骑楼、粤剧与文创小店混搭。"),
    ("太古仓码头", ["城市逛街", "美食探店"], 0, 4.5, 76, "旧仓库改造的江边码头，傍晚看日落与夜景不错。"),
    ("琶醍啤酒文化创意艺术区", ["城市逛街", "美食探店"], 0, 4.4, 74, "珠江边的啤酒厂改造园区，夜生活氛围浓。"),
    ("广州文化公园", ["城市逛街"], 0, 4.3, 55, "老城区市民公园，节庆时常有花市与展览。"),
    ("珠江夜游", ["城市逛街"], 88, 4.6, 90, "乘船夜游珠江，两岸灯光与广州塔夜景是亮点。"),
]


def _get(url: str) -> dict:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
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


def fetch_poi(name: str) -> dict:
    key = (settings.AMAP_WEB_KEY or "").strip()
    if not key:
        return {}
    params = {
        "key": key,
        "keywords": name,
        "city": CITY,
        "citylimit": "true",
        "offset": "5",
        "page": "1",
        "extensions": "all",
    }
    data = _get("https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params))
    if str(data.get("status")) != "1":
        return {}
    for poi in data.get("pois") or []:
        lnglat = str(poi.get("location") or "")
        if "," not in lnglat:
            continue
        lng, lat = lnglat.split(",")
        photos = []
        for photo in poi.get("photos") or []:
            url = str(photo.get("url") or "").strip()
            if url.startswith("http://"):
                url = "https://" + url[len("http://"):]
            if url and url not in photos:
                photos.append(url)
            if len(photos) >= MAX_PHOTOS:
                break
        return {
            "address": poi.get("address") or None,
            "lng": float(lng),
            "lat": float(lat),
            "photos": photos,
        }
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    existing = {str(s.name).strip().lower() for s in db.query(Spot).all()}
    added = 0
    skipped = 0
    failed = 0

    print("=== 计划导入 %d 个广州景点 | 模式：%s ===" % (len(SPOTS), "APPLY" if args.apply else "DRY-RUN"))
    for idx, (name, tags, price, score, heat, intro) in enumerate(SPOTS):
        if name.lower() in existing:
            skipped += 1
            print("[SKIP] %s（已存在）" % name)
            continue
        if idx:
            time.sleep(INTERVAL)
        poi = fetch_poi(name)
        if not poi:
            failed += 1
            print("[FAIL] %s（高德未查到 POI）" % name)
            continue

        payload = {
            "name": name,
            "city": CITY,
            "province": PROVINCE,
            "theme": TAG_THEME.get(tags[0], "自然风景"),
            "tags": ",".join(tags),
            "description": intro,
            "score": score,
            "price": price,
            "cover": poi["photos"][0] if poi["photos"] else None,
            "address": poi["address"],
            "heat": heat,
            "images": json.dumps(poi["photos"], ensure_ascii=False) if poi["photos"] else None,
            "lng": poi["lng"],
            "lat": poi["lat"],
        }
        print("[OK  ] %-12s %s | 图 %d 张 | %s,%s" % (name, poi["address"] or "-", len(poi["photos"]), poi["lng"], poi["lat"]))
        if args.apply:
            spot_service.create_spot(db, payload)
        existing.add(name.lower())
        added += 1

    print("\n=== 统计 ===")
    print("新增：%d 个 | 已存在跳过：%d 个 | 查不到跳过：%d 个" % (added, skipped, failed))
    if not args.apply:
        print("DRY-RUN 结束，加 --apply 才会写库。")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
