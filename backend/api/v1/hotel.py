from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.deps import require_any_auth
from core.database import get_db
from models import Hotel, HotelBooking, Trip, User
from schemas.hotel import BookingCreate, BookingListResponse, BookingOut, HotelListResponse
from services.hotel_service import build_booking_out, calc_booking, get_hotel

router = APIRouter()


def infer_hotel_type(name: str) -> str:
    """酒店类型由名称推断（表结构不变，仅用于筛选）。"""
    name = name or ""
    if "民宿" in name:
        return "民宿"
    if "电竞" in name:
        return "电竞酒店"
    if "星期八" in name:
        return "连锁酒店"
    if "西瓜" in name:
        return "商务酒店"
    return "其他酒店"


def _split_param(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


@router.get("/list", response_model=HotelListResponse)
def list_on_shelf_hotels(
    city: Optional[str] = Query(None, description="目标城市：只返回该城市酒店"),
    city_list: Optional[str] = Query(None, description="城市白名单，逗号分隔；不传=全部"),
    type: Optional[str] = Query(None, description="酒店类型，逗号分隔，多选"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_env_score: Optional[float] = Query(None, ge=0),
    min_service_score: Optional[float] = Query(None, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_auth),
):
    hotels = db.query(Hotel).filter(Hotel.status == "on_shelf")

    # 单城市隔离：目标城市唯一时，只返回该城市酒店，杜绝跨城市数据
    if city and city.strip():
        hotels = hotels.filter(Hotel.address.contains(city.strip()))

    cities = _split_param(city_list)
    if cities:
        # 地址里包含任一白名单城市即命中（如 "杭州市西湖区..." 命中 杭州）
        hotels = hotels.filter(or_(*[Hotel.address.contains(city) for city in cities]))

    if min_price is not None:
        hotels = hotels.filter(Hotel.price_per_day >= min_price)
    if max_price is not None:
        hotels = hotels.filter(Hotel.price_per_day <= max_price)
    if min_env_score is not None:
        hotels = hotels.filter(Hotel.env_score >= min_env_score)
    if min_service_score is not None:
        hotels = hotels.filter(Hotel.service_score >= min_service_score)

    items = hotels.order_by(Hotel.id.desc()).all()

    types = _split_param(type)
    if types:
        items = [h for h in items if infer_hotel_type(h.name) in types]

    return {"items": items, "total": len(items)}


@router.post("/booking", response_model=BookingOut)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_auth),
):
    hotel = get_hotel(db, payload.hotel_id)
    if hotel.status != "on_shelf":
        raise HTTPException(status_code=400, detail="该酒店已下架，无法预约")
    route_name = None
    if payload.route_id is not None:
        trip = db.query(Trip).filter(Trip.id == payload.route_id).first()
        if not trip or trip.user_id != current_user.id:
            raise HTTPException(status_code=400, detail="关联的路线不存在")
        route_name = trip.name
    days, total_price = calc_booking(hotel, payload.start_date, payload.end_date)
    booking = HotelBooking(
        user_id=current_user.id,
        hotel_id=hotel.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        days=days,
        total_price=total_price,
        status="pending",
        guest_count=payload.guest_count or 1,
        remark=payload.remark,
        route_id=payload.route_id,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return build_booking_out(booking, hotel, current_user, route_name)


@router.get("/my-booking", response_model=BookingListResponse)
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_auth),
):
    bookings = (
        db.query(HotelBooking)
        .filter(HotelBooking.user_id == current_user.id)
        .order_by(HotelBooking.id.desc())
        .all()
    )
    hotel_ids = {b.hotel_id for b in bookings}
    hotel_map = (
        {h.id: h for h in db.query(Hotel).filter(Hotel.id.in_(hotel_ids)).all()}
        if hotel_ids
        else {}
    )
    route_ids = {b.route_id for b in bookings if b.route_id}
    route_map = (
        {t.id: t.name for t in db.query(Trip).filter(Trip.id.in_(route_ids)).all()}
        if route_ids
        else {}
    )
    items = [
        build_booking_out(
            b, hotel_map.get(b.hotel_id), current_user,
            route_map.get(b.route_id) if b.route_id else None,
        )
        for b in bookings
    ]
    return {"items": items, "total": len(items)}
