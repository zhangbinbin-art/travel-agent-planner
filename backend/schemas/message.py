"""私聊消息的请求/响应结构。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.follow import FollowUserOut


class MessageSendRequest(BaseModel):
    receiver_id: int = Field(..., ge=1)
    content: str = Field(..., min_length=1, max_length=1000)


class MessageSchema(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    status: str = "normal"
    create_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    items: List[MessageSchema] = []
    total: int = 0
    can_send: bool = True
    block_reason: Optional[str] = None
    target_user: Optional[FollowUserOut] = None
