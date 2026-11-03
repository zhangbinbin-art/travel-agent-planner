"""批量生成测试用户 + 随机分散的景点点评（默认 50 用户 × 10 条 = 500 条）。

用法：
    python scripts/seed_review_users.py            # 预览（不写库）
    python scripts/seed_review_users.py --apply    # 写库

分散规则（拉丁方）：
    spot_index = (user_index + comment_index) % spot_count
    -> 每个用户的 10 条评论落在 10 个不同景点；
    -> 每个景点的 10 条评论来自 10 个不同用户，评论区不会扎堆同一个人。

说明：
    - 仅当 comments.spot_id 存在，但景点详情页的评论列表是按「帖子」聚合的，
      所以为每个入选景点建一条「游客点评合集」帖子（status=1 已通过、public），
      评论同时写入 post_id 与 spot_id，这样景点详情评论区与情感分析都能看到；
    - 幂等：用户按用户名、帖子按标题、评论按 (user_id, post_id) 判重，重复运行不会灌脏数据；
    - 只写数据，不改任何业务代码。
"""

import argparse
import json
import os
import random
import sys
from collections import Counter
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from core.hash import get_password_hash
from models import Comment, Post, Spot, User

USER_COUNT = 50
COMMENTS_PER_USER = 10
SPOT_COUNT = 50
DEFAULT_PASSWORD = "123456"
RANDOM_SEED = 20261103

OPENINGS = [
    "整体体验不错", "周末过来逛了逛", "和想象中差不多", "第一次来", "第二次打卡",
    "带家人一起过来的", "和朋友结伴来的", "淡季来人不多", "早上过来人少一些",
    "下午光线很好", "假期人有点多", "淡季体验更好", "提前做了攻略", "临时起意过来的",
    "路过顺便来看看", "专门挑了工作日", "看了评价才来的", "朋友推荐过来的",
]
DETAILS = [
    "环境干净，标识也清楚", "景色比照片更好看", "地方不算大但挺精致", "交通还算方便",
    "周边吃的很多", "门票价格比较合理", "讲解牌信息挺详细", "适合慢慢逛两三个小时",
    "拍照很出片", "人不算多，逛起来舒服", "服务人员态度不错", "停车位稍微紧张",
    "步行路线规划得还行", "夏天来要注意防晒", "雨天路有点滑", "晚上灯光很好看",
    "卫生间比较整洁", "休息区座椅挺多",
]
ENDINGS = [
    "总体值得来一次。", "下次还会再来。", "推荐给喜欢慢逛的朋友。", "性价比一般，看个人需求。",
    "体验中规中矩，没有惊喜。", "适合带孩子来。", "适合拍照发朋友圈。", "建议避开节假日。",
    "整体满意。", "有点小失望，但还行。", "体验比预期好。", "值得顺路一看。",
]


def make_content(rng: random.Random, used: set) -> str:
    for _ in range(60):
        text = "%s，%s，%s" % (
            rng.choice(OPENINGS),
            rng.choice(DETAILS),
            rng.choice(ENDINGS),
        )
        if text not in used:
            used.add(text)
            return text
    # 极端兜底：追加序号保证唯一
    text = "%s，%s，%s（%d）" % (
        rng.choice(OPENINGS),
        rng.choice(DETAILS),
        rng.choice(ENDINGS),
        len(used) + 1,
    )
    used.add(text)
    return text


def sentiment_of(score: float) -> str:
    if score >= 4.5:
        return "positive"
    if score >= 4.0:
        return "neutral"
    return "negative"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--users", type=int, default=USER_COUNT)
    parser.add_argument("--per-user", type=int, default=COMMENTS_PER_USER)
    parser.add_argument("--spots", type=int, default=SPOT_COUNT)
    args = parser.parse_args()

    rng = random.Random(RANDOM_SEED)
    db = SessionLocal()

    # ---------- 1. 测试用户 ----------
    users = []
    new_users = 0
    pwd_hash = get_password_hash(DEFAULT_PASSWORD)
    for idx in range(1, args.users + 1):
        username = "user%03d" % idx
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, password_hash=pwd_hash, role="user", audit_status="approved")
            db.add(user)
            db.flush()
            new_users += 1
        users.append(user)

    # ---------- 2. 入选景点（按评分优先，取前 N 个，保证分布稳定） ----------
    spots = (
        db.query(Spot)
        .filter(Spot.lat.isnot(None), Spot.lng.isnot(None))
        .order_by(Spot.score.desc(), Spot.id.asc())
        .limit(args.spots)
        .all()
    )
    if len(spots) < args.spots:
        print("[WARN] 可用景点不足 %d，实际使用 %d 个" % (args.spots, len(spots)))
    spot_count = len(spots)
    if not spot_count:
        print("[ERROR] 没有可用景点")
        return 2

    # ---------- 3. 每个景点一条点评合集帖子（幂等） ----------
    posts = {}
    new_posts = 0
    for index, spot in enumerate(spots):
        title = "【游客点评】%s 体验合集" % spot.name
        post = db.query(Post).filter(Post.title == title).first()
        if not post:
            post = Post(
                user_id=users[index % len(users)].id,
                title=title,
                content="%s（%s）的游客点评汇总，供出行参考。" % (spot.name, spot.city or ""),
                spot_ids=json.dumps([spot.id]),
                status=1,
                visible="public",
            )
            db.add(post)
            db.flush()
            new_posts += 1
        posts[spot.id] = post

    # ---------- 4. 评论：拉丁方分散 ----------
    used_text = set()
    created = 0
    skipped = 0
    per_spot = Counter()
    existing = {
        (c.user_id, c.post_id)
        for c in db.query(Comment.user_id, Comment.post_id).filter(Comment.post_id.isnot(None)).all()
    }

    for user_index, user in enumerate(users):
        for k in range(args.per_user):
            spot = spots[(user_index + k) % spot_count]
            post = posts[spot.id]
            key = (user.id, post.id)
            if key in existing:
                skipped += 1
                per_spot[spot.name] += 1
                continue

            score = round(rng.uniform(3.5, 5.0), 1)
            comment = Comment(
                user_id=user.id,
                spot_id=spot.id,
                post_id=post.id,
                content=make_content(rng, used_text),
                sentiment=sentiment_of(score),
                score=score,
                like_count=rng.randint(0, 6),
                status=1,
                created_at=datetime.now() - timedelta(days=rng.randint(0, 120), hours=rng.randint(0, 23)),
            )
            db.add(comment)
            existing.add(key)
            per_spot[spot.name] += 1
            created += 1

    # 帖子评论数同步（仅统计已通过评论）
    for spot_id, post in posts.items():
        count = db.query(Comment).filter(Comment.post_id == post.id, Comment.status == 1).count()
        post.comment_count = count

    if args.apply:
        db.commit()
    db.close()

    # ---------- 5. 统计 ----------
    print("=== 生成统计（%s）===" % ("APPLY" if args.apply else "DRY-RUN"))
    print("新建用户：%d 个（user001 ~ user%03d）" % (new_users, args.users))
    print("新建点评合集帖子：%d 条" % new_posts)
    print("新建评论：%d 条，跳过已存在：%d 条" % (created, skipped))
    print("覆盖景点数：%d 个" % len(per_spot))
    counts = sorted(per_spot.values())
    if counts:
        print("每个景点评论数：最少 %d / 最多 %d / 平均 %.1f" % (counts[0], counts[-1], sum(counts) / len(counts)))
        print("分布概览（前 8 个景点）：")
        for name, cnt in per_spot.most_common(8):
            print("  %-20s %d 条" % (name, cnt))
    if not args.apply:
        print("\nDRY-RUN 结束，加 --apply 才会写库。")
    else:
        print("\n测试账号密码统一为：%s" % DEFAULT_PASSWORD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
