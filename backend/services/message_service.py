"""私聊服务：单条发送限流 + 聊天记录。

限流规则：同一对用户之间，只有「最新一条消息是对方发的，或不存在消息」时才允许发送。
- 我发出后该条记为 wait_reply，在对方回复前我不能再发。
- 我回复对方时该条记为 normal，解除对方的发送限制。
"""

from typing import Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from models import Message
from models.message import MESSAGE_NORMAL, MESSAGE_WAIT_REPLY

BLOCK_REASON = "需要等对方回复之后才能继续发消息"


def _pair_condition(user_a: int, user_b: int):
    return or_(
        and_(Message.sender_id == user_a, Message.receiver_id == user_b),
        and_(Message.sender_id == user_b, Message.receiver_id == user_a),
    )


def get_latest_message(db: Session, user_a: int, user_b: int) -> Optional[Message]:
    return (
        db.query(Message)
        .filter(_pair_condition(user_a, user_b))
        .order_by(Message.id.desc())
        .first()
    )


def check_can_send(db: Session, sender_id: int, receiver_id: int) -> Tuple[bool, Optional[str]]:
    last = get_latest_message(db, sender_id, receiver_id)
    if last and last.status == MESSAGE_WAIT_REPLY and last.sender_id == sender_id:
        return False, BLOCK_REASON
    return True, None


def _resolve_status(db: Session, sender_id: int, receiver_id: int, last: Optional[Message]) -> str:
    # 最新一条是对方发来的待回复消息 → 本次属于「回复」，解除对方限制
    if last and last.sender_id != sender_id and last.status == MESSAGE_WAIT_REPLY:
        return MESSAGE_NORMAL
    return MESSAGE_WAIT_REPLY


def send_message(db: Session, sender_id: int, receiver_id: int, content: str) -> Message:
    allowed, reason = check_can_send(db, sender_id, receiver_id)
    if not allowed:
        raise ValueError(reason)
    last = get_latest_message(db, sender_id, receiver_id)
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        status=_resolve_status(db, sender_id, receiver_id, last),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_chat(db: Session, me_id: int, target_user_id: int, page: int = 1, page_size: int = 50) -> dict:
    query = db.query(Message).filter(_pair_condition(me_id, target_user_id))
    total = query.count()
    # 第 1 页返回最新的一段，再翻转成时间正序，方便前端直接渲染并滚到底部
    rows = (
        query.order_by(Message.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    rows.reverse()
    allowed, reason = check_can_send(db, me_id, target_user_id)
    return {
        "items": rows,
        "total": total,
        "can_send": allowed,
        "block_reason": reason,
    }


def list_conversations(db: Session, me_id: int) -> dict:
    """当前用户的私聊会话列表（按最新消息倒序）。

    未读口径：最新一条是对方发来的 wait_reply 消息（等我回复）即视为未读。
    blocked：双方任一拉黑即不可进入对话。
    """
    from models import User
    from services.block_service import is_blocked_either

    rows = (
        db.query(Message)
        .filter(or_(Message.sender_id == me_id, Message.receiver_id == me_id))
        .order_by(Message.id.desc())
        .all()
    )

    latest_by_peer = {}
    for message in rows:
        peer_id = message.receiver_id if message.sender_id == me_id else message.sender_id
        if peer_id in latest_by_peer:
            continue
        latest_by_peer[peer_id] = message

    if not latest_by_peer:
        return {"items": [], "total": 0, "unread_total": 0}

    users = {
        u.id: u
        for u in db.query(User).filter(User.id.in_(list(latest_by_peer.keys()))).all()
    }

    items = []
    unread_total = 0
    for peer_id, message in latest_by_peer.items():
        user = users.get(peer_id)
        if not user:
            continue
        unread = message.sender_id == peer_id and message.status == MESSAGE_WAIT_REPLY
        if unread:
            unread_total += 1
        items.append(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": getattr(user, "role", "user") or "user",
                    "avatar": None,
                },
                "last_message": {
                    "content": message.content,
                    "create_time": message.create_time,
                    "from_me": message.sender_id == me_id,
                },
                "unread": unread,
                "blocked": is_blocked_either(db, me_id, peer_id),
            }
        )

    return {"items": items, "total": len(items), "unread_total": unread_total}
