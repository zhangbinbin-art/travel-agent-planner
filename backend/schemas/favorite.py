from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from schemas.spot import SpotOut


class FavoriteBase(BaseModel):
    spot_id: int


class FavoriteOut(BaseModel):
    id: int
    user_id: int
    spot_id: int
    created_at: Optional[datetime] = None
    spot: Optional[SpotOut] = None

    class Config:
        from_attributes = True


class FavoriteListResponse(BaseModel):
    items: List[FavoriteOut]
    total: int
    page: int
    page_size: int
