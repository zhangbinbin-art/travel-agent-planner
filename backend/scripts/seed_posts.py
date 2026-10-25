import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models import Post, User

db = SessionLocal()

if db.query(Post).count() == 0:
    admin = db.query(User).filter(User.username == "admin").first()
    normal = db.query(User).filter(User.username == "favtest1").first()
    owner = normal or admin
    if owner:
        posts = [
            Post(
                user_id=owner.id,
                title="杭州西湖三日游记",
                content=(
                    "第一天：断桥残雪 - 白堤 - 平湖秋月\n"
                    "第二天：灵隐寺 - 飞来峰 - 龙井村\n"
                    "第三天：雷峰塔 - 苏堤 - 河坊街\n\n"
                    "整体体验非常好，建议清晨去断桥避开人流，"
                    "晚上可以在湖边散步看夜景。"
                ),
                heat=12,
            ),
            Post(
                user_id=(admin or owner).id,
                title="北京故宫游览攻略",
                content=(
                    "提前在官网预约门票，从午门进、神武门出，"
                    "中轴线走完大约需要 3 小时。\n"
                    "珍宝馆和钟表馆值得单独花时间。"
                ),
                heat=8,
            ),
            Post(
                user_id=owner.id,
                title="上海外滩夜景拍摄机位分享",
                content=(
                    "推荐北外滩和乍浦路桥两个机位，"
                    "日落后 30 分钟是蓝调时刻，出片率最高。"
                ),
                heat=5,
            ),
        ]
        db.add_all(posts)
        db.commit()

for p in db.query(Post).all():
    print(p.id, p.title, "user", p.user_id, "heat", p.heat)

db.close()
