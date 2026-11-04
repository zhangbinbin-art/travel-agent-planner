from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SpotBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    city: Optional[str] = None
    province: Optional[str] = None
    theme: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = 0
    price: Optional[float] = 0
    cover: Optional[str] = None
    address: Optional[str] = None
    heat: Optional[int] = 0
    images: Optional[str] = None
    # 经纬度（v0.13 新增）：后台按名称一键获取，用于地图标注与真实距离
    lat: Optional[float] = None
    lng: Optional[float] = None


class SpotCreate(SpotBase):
    pass


class SpotUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    city: Optional[str] = None
    province: Optional[str] = None
    theme: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = None
    price: Optional[float] = None
    cover: Optional[str] = None
    address: Optional[str] = None
    heat: Optional[int] = None
    images: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class SpotOut(SpotBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SpotListResponse(BaseModel):
    items: List[SpotOut]
    total: int
    page: int
    page_size: int
