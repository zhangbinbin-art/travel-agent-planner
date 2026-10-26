from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from schemas.common import UserBrief
from schemas.comment import CommentOut


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    content: Optional[str] = None
    cover: Optional[str] = None
    spot_ids: Optional[List[int]] = None


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    content: Optional[str] = None
    cover: Optional[str] = None
    spot_ids: Optional[List[int]] = None


class SpotBrief(BaseModel):
    id: int
    name: str
    city: Optional[str] = None


class PostOut(BaseModel):
    id: int
    user_id: int
    title: str
    content: Optional[str] = None
    cover: Optional[str] = None
    spot_ids: List[int] = []
    spots: List[SpotBrief] = []
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    heat: int = 0
    status: int = 0
    status_text: str = ""
    liked: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author: Optional[UserBrief] = None

    class Config:
        from_attributes = True


class PostDetailOut(PostOut):
    comments: List[CommentOut] = []


class PostListResponse(BaseModel):
    items: List[PostOut]
    total: int
    page: int
    page_size: int
