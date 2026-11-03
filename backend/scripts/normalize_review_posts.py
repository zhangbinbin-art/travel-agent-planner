"""规范「游客点评合集」帖：统一作者为系统账号，并保证广场不展示（幂等）。

用法：
    python scripts/normalize_review_posts.py            # 预览
    python scripts/normalize_review_posts.py --apply    # 执行

说明：
    - 作者统一为系统测试账号 reviewbot（密码 123456，普通用户）；
    - 可见性保持 public：景点详情页的点评区与情感统计都是按「帖子」聚合的，
      若设为 private，非作者访客将看不到这 500 条评论（与需求「点评区正常展示」冲突）；
      广场不展示改由后端列表接口按标题前缀过滤实现（见 api/v1/post.py）；
    - 只改 posts 的 author/visible，不动任何评论、用户与统计逻辑。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from core.hash import get_password_hash
from models import Post, User

SYSTEM_USERNAME = "reviewbot"
SYSTEM_PASSWORD = "123456"
TITLE_PREFIX = "【游客点评】"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    bot = db.query(User).filter(User.username == SYSTEM_USERNAME).first()
    print("系统账号：", SYSTEM_USERNAME, "存在" if bot else "不存在（将创建）")
    if not bot and args.apply:
        bot = User(
            username=SYSTEM_USERNAME,
            password_hash=get_password_hash(SYSTEM_PASSWORD),
            role="user",
            audit_status="approved",
        )
        db.add(bot)
        db.flush()
        print("[DONE] 已创建系统账号", SYSTEM_USERNAME)

    posts = db.query(Post).filter(Post.title.like(TITLE_PREFIX + "%")).all()
    print("点评合集帖：%d 条" % len(posts))
    reassigned = 0
    for post in posts:
        if bot and post.user_id != bot.id:
            post.user_id = bot.id
            reassigned += 1
        post.visible = "public"  # 保持在景点详情可见
    print("需调整作者：%d 条" % reassigned)

    if args.apply:
        db.commit()
        print("[DONE] 已写库")
    else:
        print("DRY-RUN 结束，加 --apply 才会执行。")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
