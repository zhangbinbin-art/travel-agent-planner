from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class HotelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    price_per_day: float = Field(800, ge=0)
    cover_img: Optional[str] = None
    description: Optional[str] = None
    facilities: Optional[str] = None
    env_score: Optional[float] = 0
    service_score: Optional[float] = 0


class HotelCreate(HotelBase):
    pass


class HotelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    price_per_day: Optional[float] = Field(None, ge=0)
    cover_img: Optional[str] = None
    description: Optional[str] = None
    facilities: Optional[str] = None
    env_score: Optional[float] = None
    service_score: Optional[float] = None


class HotelStatusUpdate(BaseModel):
    status: str

    def validated(self) -> str:
        if self.status not in ("on_shelf", "off_shelf"):
            raise ValueError("status must be on_shelf or off_shelf")
        return self.status


class HotelOut(BaseModel):
    id: int
    merchant_id: Optional[int] = None
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    price_per_day: float = 0
    cover_img: Optional[str] = None
    description: Optional[str] = None
    facilities: Optional[str] = None
    env_score: Optional[float] = 0
    service_score: Optional[float] = 0
    status: str = "on_shelf"
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class HotelListResponse(BaseModel):
    items: List[HotelOut]
    total: int


class BookingCreate(BaseModel):
    hotel_id: int
    start_date: date
    end_date: date
    guest_count: Optional[int] = Field(1, ge=1)
    remark: Optional[str] = None
    route_id: Optional[int] = None


class BookingStatusUpdate(BaseModel):
    status: str  # confirm / reject


class BookingOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    hotel_id: int
    hotel_name: Optional[str] = None
    start_date: date
    end_date: date
    days: int
    total_price: float
    status: str
    guest_count: int = 1
    remark: Optional[str] = None
    route_id: Optional[int] = None
    route_name: Optional[str] = None
    create_time: Optional[datetime] = None


class BookingListResponse(BaseModel):
    items: List[BookingOut]
    total: int


class DashboardOut(BaseModel):
    hotel_count: int = 0
    pending_count: int = 0
    confirm_count: int = 0
    reject_count: int = 0
    booking_total: int = 0


class MerchantAuditUpdate(BaseModel):
    audit_status: str  # approved / rejected


class MerchantOut(BaseModel):
    id: int
    username: str
    shop_name: Optional[str] = None
    audit_status: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MerchantListResponse(BaseModel):
    items: List[MerchantOut]
    total: int

class RoomBase(BaseModel):
    room_type: str = Field(..., min_length=1, max_length=100)
    image_url: Optional[str] = None
    room_price: float = Field(0, ge=0)
    bed_info: Optional[str] = None
    max_guest: int = Field(2, ge=1, le=10)
    stock: int = Field(10, ge=0, le=999)
    status: str = "free"


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    room_type: Optional[str] = Field(None, min_length=1, max_length=100)
    image_url: Optional[str] = None
    room_price: Optional[float] = Field(None, ge=0)
    bed_info: Optional[str] = None
    max_guest: Optional[int] = Field(None, ge=1, le=10)
    stock: Optional[int] = Field(None, ge=0, le=999)
    status: Optional[str] = None


class RoomOut(RoomBase):
    id: int
    hotel_id: int
    create_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoomStatusUpdate(BaseModel):
    status: str  # free / occupied / cleaning / maintenance


class OrderCreate(BaseModel):
    hotel_id: int
    room_id: Optional[int] = None
    check_in: date
    check_out: date
    people_count: Optional[int] = Field(1, ge=1, le=10)


class PayRequest(BaseModel):
    pay_channel: str  # wechat / alipay / card


class OrderOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    hotel_id: int
    hotel_name: Optional[str] = None
    room_id: Optional[int] = None
    room_type: Optional[str] = None
    room_price: Optional[float] = None
    check_in: date
    check_out: date
    days: int = 1
    people_count: int = 1
    total_price: float = 0
    pay_channel: Optional[str] = None
    order_status: str = "pending_pay"
    create_time: Optional[datetime] = None
    # 兼容旧字段名（前端历史逻辑）
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class OrderListResponse(BaseModel):
    items: List[OrderOut]
    total: int


class GuestCreate(BaseModel):
    order_id: int
    real_name: Optional[str] = None
    id_card: Optional[str] = None


class GuestOut(BaseModel):
    id: int
    order_id: int
    real_name: str
    id_card: Optional[str] = None
    checkin_time: Optional[datetime] = None
    hotel_name: Optional[str] = None
    room_type: Optional[str] = None


class BillOut(BaseModel):
    id: int
    order_id: int
    amount: float
    pay_channel: Optional[str] = None
    pay_time: Optional[datetime] = None
    hotel_name: Optional[str] = None


class ReportOut(BaseModel):
    hotel_id: int
    hotel_name: Optional[str] = None
    order_total: int = 0
    paid_total: int = 0
    revenue: float = 0
    check_in_today: int = 0
    occupancy_rate: float = 0
    daily: List[dict] = Field(default_factory=list)
