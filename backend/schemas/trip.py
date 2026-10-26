from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TripGenerateRequest(BaseModel):
    spot_ids: List[int] = Field(..., min_length=2)
    start_spot_id: int
    days: int = Field(1, ge=1, le=30)


class TripSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    spot_ids: List[int] = Field(..., min_length=2)
    start_spot_id: int
    days: int = Field(1, ge=1, le=30)


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


class BudgetItem(BaseModel):
    spot_id: int
    name: str
    ticket_price: float


class TripBudget(BaseModel):
    days: int
    items: List[BudgetItem]
    ticket_total: float
    daily_average: float


class TripGenerateResponse(BaseModel):
    route: List[RouteSpot]
    total_distance: float
    legs: List[RouteLeg]
    budget: TripBudget


class TripSummary(BaseModel):
    id: int
    name: str
    total_distance: float
    spot_count: int
    created_at: Optional[datetime] = None
    days: int = 1
    budget: Optional[TripBudget] = None


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
