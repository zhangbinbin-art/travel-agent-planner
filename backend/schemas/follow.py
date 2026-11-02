"""关注相关的请求/响应结构。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.post import PostListResponse


class FollowRequest(BaseModel):
    follow_user_id: int = Field(..., ge=1)


class FollowSchema(BaseModel):
    id: int
    user_id: int
    follow_user_id: int
    create_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class FollowUserOut(BaseModel):
    """列表里展示的用户简要信息（数据库暂无头像字段，avatar 恒为 None）。"""

    id: int
    username: str
    role: str = "user"
    avatar: Optional[str] = None
    create_time: Optional[datetime] = None


class FollowListResponse(BaseModel):
    items: List[FollowUserOut] = []
    total: int = 0
    following_count: int = 0
    follower_count: int = 0


class UserPostsResponse(PostListResponse):
    """指定用户的游记列表，附带主页展示所需的用户信息与关注状态。"""

    user: Optional[FollowUserOut] = None
    is_following: bool = False
    viewer_is_self: bool = False
    following_count: int = 0
    follower_count: int = 0
