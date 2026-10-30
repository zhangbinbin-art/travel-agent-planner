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

# ---------------------------------------------------------------------------
# v0.11 酒店预定（实名校验 + 模拟支付）
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta  # noqa: E402

from models import Bill, HotelOrder, Room  # noqa: E402
from schemas.hotel import OrderCreate, OrderListResponse, OrderOut, PayRequest  # noqa: E402

PAY_CHANNELS = ("wechat", "alipay", "card")
ORDER_TIMEOUT_MINUTES = 30


def _order_days(order) -> int:
    days = (order.check_out - order.check_in).days
    return days if days > 0 else 1


def build_order_out(order, hotel, room, user) -> dict:
    return {
        "id": order.id,
        "user_id": order.user_id,
        "username": user.username if user else None,
        "hotel_id": order.hotel_id,
        "hotel_name": hotel.name if hotel else None,
        "room_id": order.room_id,
        "room_type": room.room_type if room else None,
        "room_price": room.room_price if room else None,
        "check_in": order.check_in,
        "check_out": order.check_out,
        "days": _order_days(order),
        "people_count": order.people_count or 1,
        "total_price": order.total_price,
        "pay_channel": order.pay_channel,
        "order_status": order.order_status,
        "create_time": order.create_time,
        "start_date": order.check_in,
        "end_date": order.check_out,
    }


def expire_pending_orders(db: Session, user_id: int = None):
    """模拟超时取消：待支付超过 30 分钟自动取消（未锁库存）。"""
    threshold = datetime.now() - timedelta(minutes=ORDER_TIMEOUT_MINUTES)
    query = db.query(HotelOrder).filter(
        HotelOrder.order_status == "pending_pay", HotelOrder.create_time < threshold
    )
    if user_id is not None:
        query = query.filter(HotelOrder.user_id == user_id)
    changed = False
    for order in query.all():
        order.order_status = "cancelled"
        changed = True
    if changed:
        db.commit()


@router.post("/order", response_model=OrderOut)
def create_hotel_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_auth),
):
    if not bool(getattr(current_user, "is_real_name_auth", False)):
        raise HTTPException(status_code=403, detail="REAL_NAME_REQUIRED: 您还未完成实名认证，请前往个人中心完成实名后再预定酒店")
    hotel = get_hotel(db, payload.hotel_id)
    if hotel.status != "on_shelf":
        raise HTTPException(status_code=400, detail="该酒店已下架，无法预约")
    days, _ = calc_booking(hotel, payload.check_in, payload.check_out)

    room = None
    if payload.room_id:
        room = db.query(Room).filter(Room.id == payload.room_id, Room.hotel_id == hotel.id).first()
        if not room:
            raise HTTPException(status_code=404, detail="客房不存在")
    else:
        room = (
            db.query(Room)
            .filter(Room.hotel_id == hotel.id, Room.status == "free", Room.stock > 0)
            .order_by(Room.room_price.asc(), Room.id.asc())
            .first()
        )
    if room is None:
        raise HTTPException(status_code=400, detail="该酒店暂无可预订客房")
    if room.stock <= 0:
        raise HTTPException(status_code=400, detail="该房型已满房")

    unit_price = float(room.room_price or hotel.price_per_day or 0)
    order = HotelOrder(
        user_id=current_user.id,
        hotel_id=hotel.id,
        room_id=room.id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        people_count=payload.people_count or 1,
        total_price=round(unit_price * days, 2),
        order_status="pending_pay",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return build_order_out(order, hotel, room, current_user)


@router.get("/my-order", response_model=OrderListResponse)
def my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_auth),
):
    expire_pending_orders(db, current_user.id)
    orders = (
        db.query(HotelOrder)
        .filter(HotelOrder.user_id == current_user.id)
        .order_by(HotelOrder.id.desc())
        .all()
    )
    hotel_ids = {o.hotel_id for o in orders}
    room_ids = {o.room_id for o in orders if o.room_id}
    hotels = {h.id: h for h in db.query(Hotel).filter(Hotel.id.in_(hotel_ids)).all()} if hotel_ids else {}
    rooms = {r.id: r for r in db.query(Room).filter(Room.id.in_(room_ids)).all()} if room_ids else {}
    items = [build_order_out(o, hotels.get(o.hotel_id), rooms.get(o.room_id), current_user) for o in orders]
    return {"items": items, "total": len(items)}


@router.get("/order/{order_id}", response_model=OrderOut)
def get_hotel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_auth),
):
    expire_pending_orders(db, current_user.id)
    order = db.query(HotelOrder).filter(HotelOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.user_id != current_user.id and getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=403, detail="无权限查看该订单")
    hotel = db.query(Hotel).filter(Hotel.id == order.hotel_id).first()
    room = db.query(Room).filter(Room.id == order.room_id).first() if order.room_id else None
    owner = db.query(User).filter(User.id == order.user_id).first()
    return build_order_out(order, hotel, room, owner)


@router.post("/order/{order_id}/pay", response_model=OrderOut)
def pay_hotel_order(
    order_id: int,
    payload: PayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_auth),
):
    if payload.pay_channel not in PAY_CHANNELS:
        raise HTTPException(status_code=422, detail="支付方式只能为 wechat / alipay / card")
    expire_pending_orders(db, current_user.id)
    order = db.query(HotelOrder).filter(HotelOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作该订单")
    if order.order_status != "pending_pay":
        raise HTTPException(status_code=400, detail="当前订单状态不可支付")

    room = db.query(Room).filter(Room.id == order.room_id).first() if order.room_id else None
    if room is not None:
        if room.stock <= 0:
            raise HTTPException(status_code=400, detail="该房型已满房，无法支付")
        room.stock -= 1

    # 模拟支付 100% 成功
    order.order_status = "paid"
    order.pay_channel = payload.pay_channel
    bill = Bill(
        order_id=order.id,
        amount=order.total_price,
        pay_channel=payload.pay_channel,
        pay_time=datetime.now(),
    )
    db.add(bill)
    db.commit()
    db.refresh(order)
    hotel = db.query(Hotel).filter(Hotel.id == order.hotel_id).first()
    return build_order_out(order, hotel, room, current_user)


@router.post("/order/{order_id}/cancel", response_model=OrderOut)
def cancel_hotel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_auth),
):
    order = db.query(HotelOrder).filter(HotelOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作该订单")
    if order.order_status != "pending_pay":
        raise HTTPException(status_code=400, detail="仅待支付订单可取消")
    order.order_status = "cancelled"
    db.commit()
    db.refresh(order)
    hotel = db.query(Hotel).filter(Hotel.id == order.hotel_id).first()
    room = db.query(Room).filter(Room.id == order.room_id).first() if order.room_id else None
    return build_order_out(order, hotel, room, current_user)
