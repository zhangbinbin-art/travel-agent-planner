"""平台酒店种子数据（幂等）。

为已审核商家 shop01 写入一批虚构分店：星期八 / 西瓜 / 民宿 / 电竞酒店等。
重复执行不会重复插入（按 商家 + 酒店名称 判重，并更新价格/评分等）。

用法：python scripts/seed_hotels.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models import Hotel, User

HOTELS = [
    {
        "name": "星期八酒店·西湖店",
        "address": "杭州市西湖区北山街 88 号",
        "price_per_day": 388,
        "env_score": 4.8,
        "service_score": 4.7,
        "facilities": "免费停车,早餐,健身房,洗衣服务,24小时前台",
        "description": "步行可至西湖断桥，房间可远眺湖景，适合城市漫游与亲子出行。",
    },
    {
        "name": "星期八酒店·外滩店",
        "address": "上海市黄浦区中山东一路 18 号",
        "price_per_day": 468,
        "env_score": 4.9,
        "service_score": 4.8,
        "facilities": "江景房,行政酒廊,健身房,接机服务,会议室",
        "description": "紧邻外滩万国建筑群，夜景视野极佳，商务与观光两相宜。",
    },
    {
        "name": "星期八酒店·广州塔店",
        "address": "广州市海珠区阅江西路 222 号",
        "price_per_day": 358,
        "env_score": 4.7,
        "service_score": 4.6,
        "facilities": "江景房,自助早餐,洗衣服务,停车场",
        "description": "正对广州塔小蛮腰，夜晚灯光秀一览无余，交通便利。",
    },
    {
        "name": "西瓜酒店·苏州园林店",
        "address": "苏州市姑苏区平江路 66 号",
        "price_per_day": 298,
        "env_score": 4.6,
        "service_score": 4.5,
        "facilities": "中式庭院,茶室,早餐,行李寄存",
        "description": "藏在平江路巷弄里的园林风酒店，白墙黑瓦，安静雅致。",
    },
    {
        "name": "云栖民宿·西湖山居",
        "address": "杭州市西湖区梅灵南路 12 号",
        "price_per_day": 258,
        "env_score": 4.7,
        "service_score": 4.6,
        "facilities": "山景露台,免费早餐,茶室,烧烤区",
        "description": "半山腰的静谧民宿，推窗见茶山，适合放空与慢旅行。",
    },
    {
        "name": "电竞酒店·珠江新城店",
        "address": "广州市天河区珠江新城华夏路 9 号",
        "price_per_day": 359,
        "env_score": 4.5,
        "service_score": 4.7,
        "facilities": "高配电竞主机,双人房,零食吧,24小时前台",
        "description": "高刷显示器与电竞椅配置，双人开黑首选，亦适合年轻出行。",
    },
    {
        "name": "西瓜酒店·厦门鼓浪屿店",
        "address": "厦门市思明区鼓浪屿龙头路 35 号",
        "price_per_day": 328,
        "env_score": 4.8,
        "service_score": 4.6,
        "facilities": "海景露台,早餐,行李寄存,码头接送",
        "description": "岛上老别墅改造，步行到海边三分钟，适合度假放空。",
    },
    {
        "name": "星期八酒店·北京故宫店",
        "address": "北京市东城区南池子大街 21 号",
        "price_per_day": 428,
        "env_score": 4.7,
        "service_score": 4.8,
        "facilities": "四合院,早餐,讲解预约,行李寄存",
        "description": "距离故宫东华门步行十分钟，老北京四合院风格。",
    },
]


def main():
    db = SessionLocal()
    try:
        merchant = db.query(User).filter(User.username == "shop01").first()
        if not merchant:
            print("ERROR: merchant shop01 not found, run seed_users.py first")
            return 1
        created = updated = 0
        for item in HOTELS:
            hotel = (
                db.query(Hotel)
                .filter(Hotel.merchant_id == merchant.id, Hotel.name == item["name"])
                .first()
            )
            if hotel:
                for k, v in item.items():
                    setattr(hotel, k, v)
                hotel.status = "on_shelf"
                updated += 1
            else:
                db.add(Hotel(merchant_id=merchant.id, status="on_shelf", **item))
                created += 1
        db.commit()
        print(f"hotels created={created} updated={updated} total={db.query(Hotel).count()}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
