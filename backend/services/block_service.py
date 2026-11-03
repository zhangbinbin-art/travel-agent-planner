"""拉黑关系服务：拉黑/解除、双向判定。

语义：
    is_blocked(db, a, b)      —— a 是否拉黑了 b
    is_blocked_either(a, b)   —— 双方任一拉黑对方
    拉黑后：双方不能私聊；被拉黑方看不到对方主页与帖子。
"""

from typing import Optional

from sqlalchemy.orm import Session

from models import UserBlock


def is_blocked(db: Session, user_id: Optional[int], target_id: Optional[int]) -> bool:
    """user_id 是否拉黑了 target_id。"""
    if not user_id or not target_id or int(user_id) == int(target_id):
        return False
    return (
        db.query(UserBlock.id)
        .filter(UserBlock.user_id == int(user_id), UserBlock.blocked_user_id == int(target_id))
        .first()
        is not None
    )


def is_blocked_either(db: Session, a: Optional[int], b: Optional[int]) -> bool:
    """双方是否任一拉黑对方（用于私聊拦截）。"""
    return is_blocked(db, a, b) or is_blocked(db, b, a)


def blocked_author_ids(db: Session, viewer_id: Optional[int]) -> list:
    """返回「把 viewer 拉黑」的用户 id 列表（这些人的帖子 viewer 不可见）。"""
    if not viewer_id:
        return []
    rows = db.query(UserBlock.user_id).filter(UserBlock.blocked_user_id == int(viewer_id)).all()
    return [r[0] for r in rows]


def toggle_block(db: Session, user_id: int, target_id: int) -> dict:
    """拉黑/解除拉黑，返回最新状态。"""
    existing = (
        db.query(UserBlock)
        .filter(UserBlock.user_id == int(user_id), UserBlock.blocked_user_id == int(target_id))
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        blocked = False
    else:
        db.add(UserBlock(user_id=int(user_id), blocked_user_id=int(target_id)))
        db.commit()
        blocked = True
    return {
        "blocked": blocked,
        "blocked_by_target": is_blocked(db, target_id, user_id),
    }
