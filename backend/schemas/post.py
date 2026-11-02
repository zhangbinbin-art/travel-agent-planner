from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from schemas.common import UserBrief
from schemas.comment import CommentOut

POST_VISIBILITY = Literal["public", "friend", "private"]


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    content: Optional[str] = None
    cover: Optional[str] = None
    spot_ids: Optional[List[int]] = None
    images: Optional[List[str]] = None
    custom_spots: Optional[List[str]] = None
    visible: Optional[POST_VISIBILITY] = "public"


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    content: Optional[str] = None
    cover: Optional[str] = None
    spot_ids: Optional[List[int]] = None
    images: Optional[List[str]] = None
    custom_spots: Optional[List[str]] = None
    visible: Optional[POST_VISIBILITY] = None


class PostVisibilityUpdate(BaseModel):
    visible: POST_VISIBILITY


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
    images: List[str] = []
    spot_ids: List[int] = []
    custom_spots: List[str] = []
    spots: List[SpotBrief] = []
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    heat: int = 0
    status: int = 0
    status_text: str = ""
    visible: str = "public"
    liked: bool = False
    favorited: bool = False
    favorite_count: int = 0
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
