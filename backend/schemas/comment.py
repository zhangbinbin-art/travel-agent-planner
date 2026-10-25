from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from schemas.common import UserBrief


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    score: int = Field(5, ge=1, le=5)


class CommentOut(BaseModel):
    id: int
    post_id: Optional[int] = None
    user_id: Optional[int] = None
    content: Optional[str] = None
    score: Optional[int] = None
    created_at: Optional[datetime] = None
    author: Optional[UserBrief] = None
