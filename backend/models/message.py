"""私聊消息表。

status 语义（单条发送限流的核心状态）：
- wait_reply：该消息发送后等待对方回复，发送方在对方回复前不能再发
- normal：该消息是「回复」，发出后不再限制对方
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from core.database import Base

MESSAGE_NORMAL = "normal"
MESSAGE_WAIT_REPLY = "wait_reply"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default=MESSAGE_NORMAL,
        server_default=MESSAGE_NORMAL,
    )
    create_time = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_messages_pair", "sender_id", "receiver_id", "id"),)
