from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SpotBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    city: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = 0


class SpotCreate(SpotBase):
    pass


class SpotUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    city: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = None


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
