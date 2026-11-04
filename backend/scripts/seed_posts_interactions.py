"""用测试账号批量生成游记 + 评论 + 点赞/收藏互动。

用法：
    python scripts/seed_posts_interactions.py            # 预览
    python scripts/seed_posts_interactions.py --apply    # 写库

规则：
    - 使用 user001~user010 共 10 个账号，每人 5 篇，共 50 篇；
    - 25 篇写广州景点，25 篇写其他城市景点；
    - 每篇文笔风格不同（日记 / 攻略 / 美食 / 预算 / 拍照 / 亲子 / 独行 / 雨后 / 一日游 / 避坑）；
    - 每篇附带 3~7 条评论（来自其余测试账号），并随机产生点赞与收藏；
    - 幂等：标题带【出行记】前缀，重复运行按标题跳过。
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models import Comment, Post, PostFavorite, PostLike, Spot, User

AUTHORS = ["user%03d" % i for i in range(1, 11)]
POSTS_PER_AUTHOR = 5
GZ_COUNT = 25
OTHER_COUNT = 25
TITLE_PREFIX = "【出行记】"
RANDOM_SEED = 20261106

STYLES = [
    "日记",
    "攻略",
    "美食",
    "预算",
    "拍照",
    "亲子",
    "独行",
    "雨后",
    "一日游",
    "避坑",
]

OPENINGS = {
    "日记": ["今天起了个大早，直奔{n}", "周末临时决定去{n}走走", "第三次来{n}，感觉又不一样"],
    "攻略": ["把{n}的路线整理了一下，给要去的朋友参考", "{n}想玩得舒服，建议按这个顺序走", "去{n}之前先看这份清单"],
    "美食": ["来{n}一半是为了风景，一半是为了吃", "{n}周边的小吃比想象中丰富", "冲着吃的来{n}，结果被景色留住"],
    "预算": ["记一笔{n}的花销，方便朋友做预算", "两个人逛{n}，一天下来花得不多", "把{n}的票价和吃饭钱算了个清楚"],
    "拍照": ["{n}的光线在下午四点最好", "带着相机在{n}转了半天", "想拍出干净的构图，{n}不会让人失望"],
    "亲子": ["带孩子来{n}，体力消耗刚刚好", "{n}对小朋友友好，推车也能走", "一家三口在{n}待了大半天"],
    "独行": ["一个人去{n}，反而逛得更细", "独自在{n}坐了很久", "没有同行的人，{n}的安静刚好"],
    "雨后": ["雨后去{n}，空气里都是草木味", "{n}刚下过雨，人少了很多", "阴天的{n}比晴天更有层次"],
    "一日游": ["{n}加周边，刚好凑成一天", "从市区出发，{n}一日游路线分享", "半天{n}半天周边，节奏不赶"],
    "避坑": ["去{n}之前有几个点想提醒一下", "{n}整体不错，但这几点要注意", "把{n}容易踩的坑写下来"],
}

BODIES = [
    "景区入口有两条路，走右边那条更省力，沿途能看到{landmark}。",
    "{landmark}附近人最多，想拍空景最好早点到。",
    "门票{price}元，网上买和现场买价格一样，不用特意提前抢。",
    "中午在附近吃了点东西，人均大概{food}元，味道比预期好。",
    "停车场位置不算多，自驾的话建议十点前到。",
    "沿路指示牌清楚，跟着走不会迷路，全程大概{hours}小时。",
    "带了水和小零食，中间休息了两次，节奏比较舒服。",
    "{landmark}值得多停一会儿，细节很多，走马观花会可惜。",
    "傍晚灯光亮起来之后，整个氛围完全不同，建议留到天黑。",
    "回程路上顺道去了{landmark2}，如果时间紧可以舍掉。",
    "工作人员态度不错，问路都会耐心指。",
    "阴天来的好处是不晒，缺点是照片颜色偏灰。",
    "带孩子的话注意台阶有点多，推车不太方便。",
    "整体商业化程度可以接受，没有强制消费。",
    "厕所和休息区分布合理，走累了随时能坐下。",
]

ENDINGS = [
    "总的来说值得来一次，下次会换个季节再来。",
    "适合慢慢逛，不建议当打卡点匆匆走过。",
    "性价比不错，推荐给喜欢安静的朋友。",
    "体验中上，主要看个人兴趣。",
    "如果只安排半天，建议优先{landmark}。",
    "会推荐给第一次来{city}的朋友。",
    "这次没逛完，留了点遗憾，也算下次的理由。",
    "整体满意，唯一的问题是节假日人偏多。",
]

COMMENT_TEXTS = [
    "写得很细，已经收藏了", "这个季节去正合适", "门票价格比我想的便宜", "上周刚去过，确实人不少",
    "照片拍得好看", "请问停车方便吗？", "路线记下了，周末就去", "看完就想出发了",
    "补充一句，附近的早茶也不错", "带娃去的话推车确实费劲", "雨天去人少，体验反而更好",
    "谢谢分享，很实用", "我上次走的另一条路，也不错", "预算写得真实", "这个点我居然没发现",
    "感觉节奏安排得挺舒服", "有没有推荐的附近住宿？", "看饿了，下次专门去吃", "工作日去更舒服",
    "学到了，下次早点到", "同感，傍晚才是精华", "这篇比官方介绍实在", "已经转给朋友了",
]

SENTIMENTS = [("positive", 5), ("positive", 4.8), ("neutral", 4.2), ("neutral", 4.0), ("negative", 3.6)]


def build_content(rng, spot, style, used):
    landmark = spot.name
    others = ["周边老街", "临水步道", "观景平台", "主入口广场", "文创小店", "山腰凉亭"]
    for _ in range(40):
        parts = [rng.choice(OPENINGS[style]).format(n=landmark)]
        body_pool = BODIES[:]
        rng.shuffle(body_pool)
        for sentence in body_pool[: rng.randint(2, 4)]:
            parts.append(
                sentence.format(
                    landmark=landmark,
                    landmark2=rng.choice(others),
                    price=int(float(spot.price or 0)),
                    food=rng.randint(35, 120),
                    hours=rng.choice([2, 3, 4, 5]),
                    city=spot.city or "",
                )
            )
        parts.append(rng.choice(ENDINGS).format(landmark=landmark, city=spot.city or ""))
        text = "\n".join(parts)
        if text not in used:
            used.add(text)
            return text
    text = "\n".join(parts) + "\n（第 %d 次记录）" % (len(used) + 1)
    used.add(text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rng = random.Random(RANDOM_SEED)
    db = SessionLocal()

    authors = db.query(User).filter(User.username.in_(AUTHORS)).order_by(User.id).all()
    if len(authors) < 10:
        print("[ERROR] 测试账号不足，请先运行 scripts/seed_review_users.py")
        return 2

    gz_spots = db.query(Spot).filter(Spot.city == "广州").order_by(Spot.id).all()
    other_spots = db.query(Spot).filter(Spot.city != "广州").order_by(Spot.id).all()
    rng.shuffle(gz_spots)
    rng.shuffle(other_spots)
    if len(gz_spots) < GZ_COUNT or len(other_spots) < OTHER_COUNT:
        print("[ERROR] 景点数量不足：广州 %d / 其他 %d" % (len(gz_spots), len(other_spots)))
        return 2

    plan = []
    for i in range(GZ_COUNT):
        plan.append((gz_spots[i], "广州"))
    for i in range(OTHER_COUNT):
        plan.append((other_spots[i], "其他"))

    existing_titles = {p.title for p in db.query(Post).filter(Post.title.like(TITLE_PREFIX + "%")).all()}
    used_content = set()
    created_posts = 0
    created_comments = 0
    created_likes = 0
    created_favs = 0
    per_author = {a.username: 0 for a in authors}
    gz_posts = 0
    other_posts = 0

    style_index = 0
    for idx, (spot, region) in enumerate(plan):
        author = authors[idx % len(authors)]
        style = STYLES[style_index % len(STYLES)]
        style_index += 1
        title = "%s%s·%s视角" % (TITLE_PREFIX, spot.name, style)
        if title in existing_titles:
            continue

        content = build_content(rng, spot, style, used_content)
        images = []
        try:
            images = json.loads(spot.images) if spot.images else []
        except Exception:
            images = []
        cover = images[0] if images else spot.cover

        post = Post(
            user_id=author.id,
            title=title,
            content=content,
            cover=cover,
            images=json.dumps(images[:3], ensure_ascii=False),
            spot_ids=json.dumps([spot.id]),
            view_count=rng.randint(20, 320),
            like_count=0,
            comment_count=0,
            heat=rng.randint(10, 90),
            status=1,
            visible="public",
            created_at=datetime.now() - timedelta(days=rng.randint(0, 45), hours=rng.randint(0, 23)),
        )
        print("[POST] %-8s %-24s %s" % (author.username, spot.name, style))
        if not args.apply:
            created_posts += 1
            gz_posts += 1 if region == "广州" else 0
            other_posts += 1 if region != "广州" else 0
            per_author[author.username] += 1
            continue

        db.add(post)
        db.flush()

        # 评论：从其他测试账号里随机挑 3~7 个
        commenters = [a for a in authors if a.id != author.id]
        rng.shuffle(commenters)
        picked = commenters[: rng.randint(3, 7)]
        for c_user in picked:
            sentiment, score = rng.choice(SENTIMENTS)
            db.add(
                Comment(
                    user_id=c_user.id,
                    spot_id=spot.id,
                    post_id=post.id,
                    content=rng.choice(COMMENT_TEXTS),
                    sentiment=sentiment,
                    score=score,
                    like_count=rng.randint(0, 8),
                    status=1,
                    created_at=datetime.now() - timedelta(days=rng.randint(0, 40), hours=rng.randint(0, 23)),
                )
            )
            created_comments += 1

        # 点赞 / 收藏互动
        likers = rng.sample(authors, rng.randint(1, 6))
        for liker in likers:
            db.add(PostLike(user_id=liker.id, post_id=post.id))
            created_likes += 1
        favers = rng.sample(authors, rng.randint(0, 3))
        for faver in favers:
            db.add(PostFavorite(user_id=faver.id, post_id=post.id))
            created_favs += 1

        post.comment_count = len(picked)
        post.like_count = len(likers)
        created_posts += 1
        gz_posts += 1 if region == "广州" else 0
        other_posts += 1 if region != "广州" else 0
        per_author[author.username] += 1

    if args.apply:
        db.commit()

    print("\n=== 统计 ===")
    print("新增游记：%d 篇（广州 %d / 其他地区 %d）" % (created_posts, gz_posts, other_posts))
    print("新增评论：%d 条 | 点赞：%d 个 | 收藏：%d 个" % (created_comments, created_likes, created_favs))
    print("每位作者：", per_author)
    if not args.apply:
        print("DRY-RUN 结束，加 --apply 才会写库。")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
