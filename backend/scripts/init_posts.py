import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect

from core.database import engine, SessionLocal
from models import Post, Comment, PostLike, CommentLike


EXPECTED = {
    "posts": {
        "id", "user_id", "title", "content", "cover", "spot_ids",
        "view_count", "like_count", "comment_count", "heat", "status",
        "created_at", "updated_at",
    },
    "comments": {
        "id", "user_id", "spot_id", "post_id", "content", "sentiment",
        "score", "like_count", "status", "created_at",
    },
    "post_likes": {"id", "user_id", "post_id", "created_at"},
    "comment_likes": {"id", "user_id", "comment_id", "created_at"},
}


def main():
    db = SessionLocal()
    try:
        # drop only the four post/comment tables, in dependency order
        CommentLike.__table__.drop(bind=engine, checkfirst=True)
        PostLike.__table__.drop(bind=engine, checkfirst=True)
        Comment.__table__.drop(bind=engine, checkfirst=True)
        Post.__table__.drop(bind=engine, checkfirst=True)

        # recreate in reverse dependency order
        Post.__table__.create(bind=engine, checkfirst=True)
        Comment.__table__.create(bind=engine, checkfirst=True)
        PostLike.__table__.create(bind=engine, checkfirst=True)
        CommentLike.__table__.create(bind=engine, checkfirst=True)

        # verify schema
        inspector = inspect(engine)
        problems = []
        for table, expected_cols in EXPECTED.items():
            actual = {c["name"] for c in inspector.get_columns(table)}
            missing = expected_cols - actual
            if missing:
                problems.append("%s missing %s" % (table, sorted(missing)))
        if problems:
            print("ERR schema mismatch: " + "; ".join(problems))
            sys.exit(1)

        print("OK init_posts done")
    except SystemExit:
        raise
    except Exception as exc:
        print("ERR " + str(exc))
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
