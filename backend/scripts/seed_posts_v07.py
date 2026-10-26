import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from core.database import SessionLocal
from models import Comment, Post, Spot, User
from services import post_service

POSTS_SEED = [
    {
        "author": "favtest1",
        "title": "杭州西湖三日游全攻略",
        "content": (
            "第一天：断桥残雪 - 白堤 - 平湖秋月\n"
            "第二天：灵隐寺 - 飞来峰 - 龙井村\n"
            "第三天：雷峰塔 - 苏堤 - 河坊街\n\n"
            "十月的杭州天气非常好，建议清晨去断桥避开人流，"
            "晚上可以在湖边散步，夜风很舒服。"
        ),
        "cover": "https://picsum.photos/seed/xihu/800/450",
        "spot_names": ["西湖景区"],
        "view_count": 10,
        "like_count": 2,
    },
    {
        "author": "admin",
        "title": "故宫深度游：一日看遍三大殿",
        "content": (
            "提前在官方渠道预约门票，早点进园可以避开旅行团。\n"
            "路线建议：午门 - 太和殿 - 中和殿 - 保和殿 - 珍宝馆 - 御花园。\n"
            "珍宝馆和钟表馆值得单独花时间慢慢看，全程大约需要 3 小时。"
        ),
        "cover": "https://picsum.photos/seed/gugong/800/450",
        "spot_names": ["故宫博物院"],
        "view_count": 5,
        "like_count": 1,
    },
    {
        "author": "favtest1",
        "title": "上海外滩夜景机位推荐",
        "content": (
            "推荐两个看夜景的机位：外滩亲水平台和陆家嘴滨江步道。\n"
            "外滩这边晚上 19:00 之后灯光全开，拍对岸三件套非常出片；\n"
            "如果想拍外滩万国建筑群，就去对岸的滨江步道。"
        ),
        "cover": "https://picsum.photos/seed/waitan/800/450",
        "spot_names": ["西湖景区", "外滩"],
        "view_count": 3,
        "like_count": 0,
    },
]

COMMENTS_SEED = [
    {"author": "favtest1", "spot": "西湖景区", "content": "太美了，非常值得去，清晨人少风景好", "score": 5},
    {"author": "user", "spot": "西湖景区", "content": "景色不错，就是节假日人有点多", "score": 4},
    {"author": "1111", "spot": "西湖景区", "content": "门票免费太良心了，还会再来", "score": 5},
    {"author": "favtest1", "spot": "故宫博物院", "content": "讲解很专业，展品丰富，强烈推荐", "score": 5},
    {"author": "user", "spot": "故宫博物院", "content": "排队时间太长了，体验一般", "score": 3},
    {"author": "1111", "spot": "外滩", "content": "夜景绝美，值得专门来一趟", "score": 5},
    {"author": "user", "spot": "西湖景区", "content": "一般般吧", "score": 3},
    {"author": "1111", "spot": "故宫博物院", "content": "也就那样吧", "score": 3},
    {"author": "favtest2", "spot": "外滩", "content": "普普通通", "score": 3},
    {"author": "favtest2", "post_index": 0, "content": "攻略很实用，收藏了", "score": 5},
    {"author": "user", "post_index": 1, "content": "珍宝馆确实值得单独留时间", "score": 4},
]


def main():
    db = SessionLocal()
    try:
        if db.query(Post).count() > 0:
            print("SKIP posts not empty")
            return

        spots = {s.name: s for s in db.query(Spot).all()}
        users = {u.username: u for u in db.query(User).all()}
        if not spots:
            print("ERR no spots")
            sys.exit(1)
        if not users:
            print("ERR no users")
            sys.exit(1)
        fallback_user = next(iter(users.values()))

        created_posts = []
        for item in POSTS_SEED:
            spot_ids = [spots[name].id for name in item["spot_names"] if name in spots]
            author = users.get(item["author"], fallback_user)
            post = Post(
                user_id=author.id,
                title=item["title"],
                content=item["content"],
                cover=item["cover"],
                spot_ids=json.dumps(spot_ids),
                status=1,
                view_count=item["view_count"],
                like_count=item["like_count"],
                comment_count=0,
            )
            post_service.recompute_heat(post)
            db.add(post)
            db.commit()
            db.refresh(post)
            created_posts.append(post)

        for item in COMMENTS_SEED:
            author = users.get(item["author"], fallback_user)
            spot_id = spots[item["spot"]].id if item.get("spot") in spots else None
            post_id = created_posts[item["post_index"]].id if "post_index" in item else None
            db.add(
                Comment(
                    user_id=author.id,
                    spot_id=spot_id,
                    post_id=post_id,
                    content=item["content"],
                    score=item["score"],
                    status=1,
                    like_count=0,
                )
            )
        db.commit()

        for post in created_posts:
            post.comment_count = db.query(Comment).filter(Comment.post_id == post.id).count()
            post_service.recompute_heat(post)
        db.commit()

        print(
            "OK seed_posts_v07 posts=%d comments=%d spots=%d users=%d"
            % (
                db.query(Post).count(),
                db.query(Comment).count(),
                db.query(Spot).count(),
                db.query(User).count(),
            )
        )
    except Exception as exc:
        print("ERR", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
