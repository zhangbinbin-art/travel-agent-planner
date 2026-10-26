from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TripGenerateRequest(BaseModel):
    spot_ids: List[int] = Field(..., min_length=2)
    start_spot_id: int


class TripSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    spot_ids: List[int] = Field(..., min_length=2)
    start_spot_id: int


class RouteSpot(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    score: Optional[float] = 0
    x: float
    y: float
    order: int


class RouteLeg(BaseModel):
    from_spot_id: int
    to_spot_id: int
    distance: float


class TripGenerateResponse(BaseModel):
    route: List[RouteSpot]
    total_distance: float
    legs: List[RouteLeg]


class TripSummary(BaseModel):
    id: int
    name: str
    total_distance: float
    spot_count: int
    created_at: Optional[datetime] = None


class TripListResponse(BaseModel):
    items: List[TripSummary]
    total: int
    page: int
    page_size: int


class TripDetail(TripSummary):
    user_id: int
    route: List[RouteSpot]
    legs: List[RouteLeg]
    start_spot_id: Optional[int] = None
