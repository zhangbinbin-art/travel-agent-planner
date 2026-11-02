"""关注关系服务：关注/取关、关注列表、粉丝列表。"""

from typing import Optional

from sqlalchemy.orm import Session

from models import Follow, User


def build_user_brief(user: Optional[User], create_time=None) -> Optional[dict]:
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "role": getattr(user, "role", "user") or "user",
        # 项目没有头像字段，前端统一用用户名首字母生成头像
        "avatar": None,
        "create_time": create_time,
    }


def is_following(db: Session, user_id: Optional[int], target_user_id: int) -> bool:
    if not user_id or not target_user_id or int(user_id) == int(target_user_id):
        return False
    return (
        db.query(Follow.id)
        .filter(Follow.user_id == user_id, Follow.follow_user_id == target_user_id)
        .first()
        is not None
    )


def count_following(db: Session, user_id: int) -> int:
    return db.query(Follow).filter(Follow.user_id == user_id).count()


def count_fans(db: Session, user_id: int) -> int:
    return db.query(Follow).filter(Follow.follow_user_id == user_id).count()


def toggle_follow(db: Session, user_id: int, target_user_id: int) -> dict:
    existing = (
        db.query(Follow)
        .filter(Follow.user_id == user_id, Follow.follow_user_id == target_user_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        following = False
    else:
        db.add(Follow(user_id=user_id, follow_user_id=target_user_id))
        db.commit()
        following = True
    return {
        "following": following,
        "follower_count": count_fans(db, target_user_id),
        "following_count": count_following(db, user_id),
    }


def _list_users(db: Session, owner_column, owner_id: int, page: int = 1, page_size: int = 20) -> dict:
    base_query = db.query(Follow).filter(owner_column == owner_id)
    total = base_query.count()
    rows = (
        base_query.order_by(Follow.create_time.desc(), Follow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    target_ids = [r.follow_user_id if owner_column is Follow.user_id else r.user_id for r in rows]
    users = {}
    if target_ids:
        users = {u.id: u for u in db.query(User).filter(User.id.in_(target_ids)).all()}
    items = []
    for row in rows:
        uid = row.follow_user_id if owner_column is Follow.user_id else row.user_id
        brief = build_user_brief(users.get(uid), row.create_time)
        if brief:
            items.append(brief)
    return {
        "items": items,
        "total": total,
        "following_count": count_following(db, owner_id),
        "follower_count": count_fans(db, owner_id),
    }


def list_following(db: Session, user_id: int, page: int = 1, page_size: int = 20) -> dict:
    return _list_users(db, Follow.user_id, user_id, page=page, page_size=page_size)


def list_fans(db: Session, user_id: int, page: int = 1, page_size: int = 20) -> dict:
    return _list_users(db, Follow.follow_user_id, user_id, page=page, page_size=page_size)
