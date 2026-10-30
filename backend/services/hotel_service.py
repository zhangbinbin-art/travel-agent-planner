from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Hotel, HotelBooking, User


def get_merchant_hotel(db: Session, merchant_id: int, hotel_id: int) -> Hotel:
    hotel = (
        db.query(Hotel)
        .filter(Hotel.id == hotel_id, Hotel.merchant_id == merchant_id)
        .first()
    )
    if not hotel:
        raise HTTPException(status_code=404, detail="酒店不存在")
    return hotel


def get_hotel(db: Session, hotel_id: int) -> Hotel:
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="酒店不存在")
    return hotel


def build_booking_out(
    booking: HotelBooking,
    hotel: Hotel,
    user: User,
    route_name: str = None,
) -> dict:
    return {
        "id": booking.id,
        "user_id": booking.user_id,
        "username": user.username if user else None,
        "hotel_id": booking.hotel_id,
        "hotel_name": hotel.name if hotel else None,
        "start_date": booking.start_date,
        "end_date": booking.end_date,
        "days": booking.days,
        "total_price": booking.total_price,
        "status": booking.status,
        "guest_count": getattr(booking, "guest_count", 1) or 1,
        "remark": getattr(booking, "remark", None),
        "route_id": getattr(booking, "route_id", None),
        "route_name": route_name,
        "create_time": booking.create_time,
    }


def calc_booking(hotel: Hotel, start_date: date, end_date: date) -> tuple[int, float]:
    """按入住区间计算天数与总价：days = 离店 - 入住（至少 1 天）。"""
    days = (end_date - start_date).days
    if days <= 0:
        raise HTTPException(status_code=400, detail="离店日期必须晚于入住日期")
    total = round(days * float(hotel.price_per_day or 0), 2)
    return days, total
