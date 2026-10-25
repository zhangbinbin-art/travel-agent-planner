from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from schemas.common import UserBrief
from schemas.comment import CommentOut


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    content: Optional[str] = None


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    content: Optional[str] = None


class PostOut(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    heat: int = 0
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    author: Optional[UserBrief] = None


class PostDetailOut(PostOut):
    comments: List[CommentOut] = []


class PostListResponse(BaseModel):
    items: List[PostOut]
    total: int
    page: int
    page_size: int
