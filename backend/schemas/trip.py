from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SmartRecommendRequest(BaseModel):
    """纯智能规划：单目的地、偏好驱动。"""
    start_lat: Optional[float] = None
    start_lng: Optional[float] = None
    start_location: Optional[str] = None
    target_city: str = Field(..., min_length=1, max_length=50)
    travel_type: str = Field("单人出行")
    preferences: List[str] = Field(default_factory=list)
    days: int = Field(1, ge=1, le=10)
    hotel_per_day: Optional[float] = Field(None, ge=0, le=100000)
    # 酒店筛选条件（可选，用于推荐同城酒店）
    hotel_types: List[str] = Field(default_factory=list)
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    min_env_score: Optional[float] = Field(None, ge=0)
    min_service_score: Optional[float] = Field(None, ge=0)
    hotel_features: List[str] = Field(default_factory=list)


class DayPlan(BaseModel):
    day: int
    spot_ids: List[int]
    spot_names: List[str]


class SmartRecommendResponse(BaseModel):
    route: List["RouteSpot"]
    total_distance: float
    legs: List["RouteLeg"]
    budget: "TripBudget"
    day_plans: List[DayPlan] = Field(default_factory=list)
    recommended_hotels: List[dict] = Field(default_factory=list)
    target_city: str = ""
    start_location: Optional[str] = None


class TripGenerateRequest(BaseModel):
    spot_ids: List[int] = Field(..., min_length=2)
    start_spot_id: int
    days: int = Field(1, ge=1, le=30)
    hotel_per_day: Optional[float] = Field(None, ge=0, le=100000)


class TripSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    # v0.10 智能规划可能只命中单景点城市的 1 个景点，允许保存 1 个
    spot_ids: List[int] = Field(..., min_length=1)
    start_spot_id: int
    days: int = Field(1, ge=1, le=30)
    hotel_per_day: Optional[float] = Field(None, ge=0, le=100000)


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
    hotel_total: float
    traffic_total: float
    grand_total: float
    daily_avg: float          # 总预算日均 = grand_total / days
    daily_average: float = 0  # 兼容 v0.8：门票日均 = ticket_total / days（保留，勿删）


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


SmartRecommendResponse.model_rebuild()
