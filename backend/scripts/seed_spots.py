import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import SessionLocal, engine
from models import Spot

# 兼容旧库：补充新增列（province / theme / price / cover），可重复执行
def ensure_columns():
    insp = inspect(engine)
    existing = {col["name"] for col in insp.get_columns(Spot.__tablename__)}
    ddl = {
        "province": "VARCHAR(50) NULL",
        "theme": "VARCHAR(50) NULL",
        "price": "FLOAT NULL DEFAULT 0",
        "cover": "VARCHAR(255) NULL",
    }
    with engine.begin() as conn:
        for name, typ in ddl.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {Spot.__tablename__} ADD COLUMN {name} {typ}"))


ensure_columns()

db = SessionLocal()

COVERS = {
    "自然风景": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
    "历史古迹": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?auto=format&fit=crop&w=800&q=80",
    "城市观光": "https://images.unsplash.com/photo-1519501025264-65ba15a82390?auto=format&fit=crop&w=800&q=80",
    "主题乐园": "https://images.unsplash.com/photo-1566127992631-137a642a90f4?auto=format&fit=crop&w=800&q=80",
}

spots = [
    {"name": "西湖景区", "city": "杭州", "province": "浙江", "theme": "自然风景", "tags": "自然风景", "score": 4.9, "price": 0, "description": "湖光山色，著名风景名胜区"},
    {"name": "故宫博物院", "city": "北京", "province": "北京", "theme": "历史古迹", "tags": "历史古迹", "score": 4.9, "price": 60, "description": "明清两代皇家宫殿"},
    {"name": "外滩", "city": "上海", "province": "上海", "theme": "城市观光", "tags": "城市观光", "score": 4.8, "price": 0, "description": "万国建筑博览群，夜景绝美"},
    {"name": "白云山", "city": "广州", "province": "广东", "theme": "自然风景", "tags": "自然风景", "score": 4.7, "price": 5, "description": "南粤名山，登高俯瞰广州城区，山林绿植丰富"},
    {"name": "长隆野生动物世界", "city": "广州", "province": "广东", "theme": "主题乐园", "tags": "主题乐园", "score": 4.8, "price": 250, "description": "世界级野生动物园，可以自驾观赏各类野生动物"},
    {"name": "灵隐寺", "city": "杭州", "province": "浙江", "theme": "历史古迹", "tags": "历史古迹", "score": 4.6, "price": 75, "description": "千年古刹，杭州知名佛教名胜，山林清幽（飞来峰45元+香花券30元）"},
    {"name": "八达岭长城", "city": "北京", "province": "北京", "theme": "历史古迹", "tags": "历史古迹", "score": 4.7, "price": 40, "description": "万里长城的经典段落，明代边防古迹"},
    {"name": "迪士尼乐园", "city": "上海", "province": "上海", "theme": "主题乐园", "tags": "主题乐园", "score": 4.7, "price": 435, "description": "国内迪士尼主题乐园，童话游玩项目"},
    {"name": "漓江", "city": "桂林", "province": "广西", "theme": "自然风景", "tags": "自然风景", "score": 4.9, "price": 190, "description": "桂林山水代表，喀斯特峰林沿江风光（竹筏票190元）"},
    {"name": "鼓浪屿", "city": "厦门", "province": "福建", "theme": "自然风景", "tags": "自然风景", "score": 4.6, "price": 35, "description": "海岛文艺景点，近代万国建筑，无机动车（船票35元）"},
    {"name": "拙政园", "city": "苏州", "province": "江苏", "theme": "历史古迹", "tags": "历史古迹", "score": 4.7, "price": 70, "description": "中国四大名园，古典江南园林代表"},
    {"name": "珠海长隆海洋王国", "city": "珠海", "province": "广东", "theme": "主题乐园", "tags": "主题乐园", "score": 4.8, "price": 365, "description": "大型海洋主题乐园，海洋动物与表演"},
    {"name": "乌镇", "city": "嘉兴", "province": "浙江", "theme": "历史古迹", "tags": "历史古迹", "score": 4.6, "price": 110, "description": "江南水乡古镇，白墙黑瓦流水人家"},
    {"name": "雷峰塔", "city": "杭州", "province": "浙江", "theme": "历史古迹", "tags": "历史古迹", "score": 4.7, "price": 40, "description": "西湖十景之一，登塔俯瞰西湖全景，白蛇传说地"},
    {"name": "宋城", "city": "杭州", "province": "浙江", "theme": "主题乐园", "tags": "主题乐园", "score": 4.6, "price": 320, "description": "宋文化主题乐园，大型实景演出《宋城千古情》"},
]

for s in spots:
    s.setdefault("cover", COVERS.get(s.get("theme")))
    exists = db.query(Spot).filter(Spot.name == s["name"]).first()
    if not exists:
        db.add(Spot(**s))
    else:
        for k, v in s.items():
            setattr(exists, k, v)

db.commit()
print(db.query(Spot).count())
db.close()
