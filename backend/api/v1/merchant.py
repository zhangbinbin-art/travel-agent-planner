from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import require_merchant, require_merchant_hotel
from core.database import get_db
from services import hotel_audit_service
from models import Bill, GuestRecord, Hotel, HotelOrder, Room, User
from schemas.hotel_audit import HotelCertUpsert, HotelProfileUpsert
from schemas.hotel import (
    BillOut,
    DashboardOut,
    GuestCreate,
    GuestOut,
    HotelOut,
    OrderListResponse,
    OrderOut,
    ReportOut,
    RoomCreate,
    RoomOut,
    RoomStatusUpdate,
    RoomUpdate,
)

router = APIRouter()


def _days(order) -> int:
    d = (order.check_out - order.check_in).days
    return d if d > 0 else 1


def _order_out(order, hotel, room, user) -> dict:
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
        "days": _days(order),
        "people_count": order.people_count or 1,
        "total_price": order.total_price,
        "pay_channel": order.pay_channel,
        "order_status": order.order_status,
        "create_time": order.create_time,
        "start_date": order.check_in,
        "end_date": order.check_out,
    }


@router.get("/hotel", response_model=HotelOut)
def my_hotel(db: Session = Depends(get_db), hotel_id: int = Depends(require_merchant_hotel)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="酒店不存在")
    return hotel


# ---------------------------------------------------------------------------
# 客房管理
# ---------------------------------------------------------------------------

@router.get("/room", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db), hotel_id: int = Depends(require_merchant_hotel)):
    return db.query(Room).filter(Room.hotel_id == hotel_id).order_by(Room.id.desc()).all()


def _require_verified(db: Session, shop: User) -> None:
    status = hotel_audit_service.merchant_status(db, shop.id, shop)
    if not status["verified"]:
        raise HTTPException(
            status_code=403,
            detail="酒店资料与资质认证审核通过后才能新增客房",
        )


@router.post("/room", response_model=RoomOut)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    hotel_id: int = Depends(require_merchant_hotel),
    shop: User = Depends(require_merchant),
):
    # 酒店资料 + 资质认证双通过后才允许新增客房
    _require_verified(db, shop)
    room = Room(hotel_id=hotel_id, **payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.put("/room/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    hotel_id: int = Depends(require_merchant_hotel),
):
    room = db.query(Room).filter(Room.id == room_id, Room.hotel_id == hotel_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="客房不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(room, key, value)
    db.commit()
    db.refresh(room)
    return room


@router.put("/room/{room_id}/status", response_model=RoomOut)
def update_room_status(
    room_id: int,
    payload: RoomStatusUpdate,
    db: Session = Depends(get_db),
    hotel_id: int = Depends(require_merchant_hotel),
):
    if payload.status not in ("free", "occupied", "cleaning", "maintenance"):
        raise HTTPException(status_code=422, detail="房间状态非法")
    room = db.query(Room).filter(Room.id == room_id, Room.hotel_id == hotel_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="客房不存在")
    room.status = payload.status
    db.commit()
    db.refresh(room)
    return room


@router.delete("/room/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    hotel_id: int = Depends(require_merchant_hotel),
):
    room = db.query(Room).filter(Room.id == room_id, Room.hotel_id == hotel_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="客房不存在")
    db.delete(room)
    db.commit()
    return {"message": "删除成功"}


# ---------------------------------------------------------------------------
# 预定订单
# ---------------------------------------------------------------------------

@router.get("/order", response_model=OrderListResponse)
def list_orders(
    order_status: str = Query(""),
    db: Session = Depends(get_db),
    hotel_id: int = Depends(require_merchant_hotel),
):
    query = db.query(HotelOrder).filter(HotelOrder.hotel_id == hotel_id)
    if order_status:
        query = query.filter(HotelOrder.order_status == order_status)
    orders = query.order_by(HotelOrder.id.desc()).all()
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    user_ids = {o.user_id for o in orders}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    room_ids = {o.room_id for o in orders if o.room_id}
    rooms = {r.id: r for r in db.query(Room).filter(Room.id.in_(room_ids)).all()} if room_ids else {}
    items = [_order_out(o, hotel, rooms.get(o.room_id), users.get(o.user_id)) for o in orders]
    return {"items": items, "total": len(items)}


@router.put("/order/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: RoomStatusUpdate,
    db: Session = Depends(get_db),
    hotel_id: int = Depends(require_merchant_hotel),
):
    if payload.status not in ("checked_in", "checked_out", "cancelled", "paid"):
        raise HTTPException(status_code=422, detail="订单状态非法")
    order = db.query(HotelOrder).filter(HotelOrder.id == order_id, HotelOrder.hotel_id == hotel_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    room = db.query(Room).filter(Room.id == order.room_id).first() if order.room_id else None
    order.order_status = payload.status
    if payload.status == "checked_in" and room:
        room.status = "occupied"
        # 办理入住时自动补一条客人登记记录（幂等，已存在则跳过）
        existing_guest = db.query(GuestRecord).filter(GuestRecord.order_id == order.id).first()
        if not existing_guest:
            guest_user = db.query(User).filter(User.id == order.user_id).first()
            db.add(
                GuestRecord(
                    order_id=order.id,
                    real_name=(
                        (guest_user.real_name if guest_user else None)
                        or (guest_user.username if guest_user else None)
                        or "客人"
                    ),
                    id_card=(guest_user.id_card if guest_user else None),
                    checkin_time=datetime.now(),
                )
            )
    if payload.status == "checked_out" and room:
        room.status = "cleaning"
    if payload.status == "cancelled" and room and order.pay_channel:
        room.stock = int(room.stock or 0) + 1
    db.commit()
    db.refresh(order)
    hotel = db.query(Hotel).filter(Hotel.id == order.hotel_id).first()
    user = db.query(User).filter(User.id == order.user_id).first()
    return _order_out(order, hotel, room, user)


# ---------------------------------------------------------------------------
# 客人登记
# ---------------------------------------------------------------------------

@router.get("/guest", response_model=list[GuestOut])
def list_guests(db: Session = Depends(get_db), hotel_id: int = Depends(require_merchant_hotel)):
    order_ids = [
        row[0] for row in db.query(HotelOrder.id).filter(HotelOrder.hotel_id == hotel_id).all()
    ]
    if not order_ids:
        return []
    guests = (
        db.query(GuestRecord)
        .filter(GuestRecord.order_id.in_(order_ids))
        .order_by(GuestRecord.id.desc())
        .all()
    )
    orders = {o.id: o for o in db.query(HotelOrder).filter(HotelOrder.id.in_(order_ids)).all()}
    rooms = {r.id: r for r in db.query(Room).filter(Room.hotel_id == hotel_id).all()}
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    result = []
    for g in guests:
        order = orders.get(g.order_id)
        room = rooms.get(order.room_id) if order and order.room_id else None
        result.append(
            {
                "id": g.id,
                "order_id": g.order_id,
                "real_name": g.real_name,
                "id_card": g.id_card,
                "checkin_time": g.checkin_time,
                "hotel_name": hotel.name if hotel else None,
                "room_type": room.room_type if room else None,
            }
        )
    return result


@router.post("/guest", response_model=GuestOut)
def checkin_guest(
    payload: GuestCreate,
    db: Session = Depends(get_db),
    hotel_id: int = Depends(require_merchant_hotel),
):
    order = db.query(HotelOrder).filter(HotelOrder.id == payload.order_id, HotelOrder.hotel_id == hotel_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.order_status not in ("paid", "checked_in"):
        raise HTTPException(status_code=400, detail="仅已支付订单可办理入住")
    user = db.query(User).filter(User.id == order.user_id).first()
    existing = db.query(GuestRecord).filter(GuestRecord.order_id == order.id).first()
    if existing:
        return {
            "id": existing.id,
            "order_id": existing.order_id,
            "real_name": existing.real_name,
            "id_card": existing.id_card,
            "checkin_time": existing.checkin_time,
            "hotel_name": None,
            "room_type": None,
        }
    guest = GuestRecord(
        order_id=order.id,
        real_name=(payload.real_name or (user.real_name if user else None) or (user.username if user else "客人")),
        id_card=payload.id_card or (user.id_card if user else None),
        checkin_time=datetime.now(),
    )
    db.add(guest)
    order.order_status = "checked_in"
    room = db.query(Room).filter(Room.id == order.room_id).first() if order.room_id else None
    if room:
        room.status = "occupied"
    db.commit()
    db.refresh(guest)
    return {
        "id": guest.id,
        "order_id": guest.order_id,
        "real_name": guest.real_name,
        "id_card": guest.id_card,
        "checkin_time": guest.checkin_time,
        "hotel_name": None,
        "room_type": room.room_type if room else None,
    }


# ---------------------------------------------------------------------------
# 账单收银
# ---------------------------------------------------------------------------

@router.get("/bill", response_model=list[BillOut])
def list_bills(db: Session = Depends(get_db), hotel_id: int = Depends(require_merchant_hotel)):
    order_ids = [
        row[0] for row in db.query(HotelOrder.id).filter(HotelOrder.hotel_id == hotel_id).all()
    ]
    if not order_ids:
        return []
    bills = (
        db.query(Bill)
        .filter(Bill.order_id.in_(order_ids))
        .order_by(Bill.id.desc())
        .all()
    )
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    return [
        {
            "id": b.id,
            "order_id": b.order_id,
            "amount": b.amount,
            "pay_channel": b.pay_channel,
            "pay_time": b.pay_time,
            "hotel_name": hotel.name if hotel else None,
        }
        for b in bills
    ]


@router.post("/bill/{order_id}/settle", response_model=BillOut)
def settle_bill(
    order_id: int,
    db: Session = Depends(get_db),
    hotel_id: int = Depends(require_merchant_hotel),
):
    order = db.query(HotelOrder).filter(HotelOrder.id == order_id, HotelOrder.hotel_id == hotel_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    bill = db.query(Bill).filter(Bill.order_id == order.id).first()
    if not bill:
        bill = Bill(
            order_id=order.id,
            amount=order.total_price,
            pay_channel=order.pay_channel or "offline",
            pay_time=datetime.now(),
        )
        db.add(bill)
    order.order_status = "checked_out"
    room = db.query(Room).filter(Room.id == order.room_id).first() if order.room_id else None
    if room:
        room.status = "cleaning"
    db.commit()
    db.refresh(bill)
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    return {
        "id": bill.id,
        "order_id": bill.order_id,
        "amount": bill.amount,
        "pay_channel": bill.pay_channel,
        "pay_time": bill.pay_time,
        "hotel_name": hotel.name if hotel else None,
    }


# ---------------------------------------------------------------------------
# 财务报表 & 仪表盘
# ---------------------------------------------------------------------------

@router.get("/report", response_model=ReportOut)
def report(db: Session = Depends(get_db), hotel_id: int = Depends(require_merchant_hotel)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    orders = db.query(HotelOrder).filter(HotelOrder.hotel_id == hotel_id).all()
    order_ids = [o.id for o in orders]
    bills = db.query(Bill).filter(Bill.order_id.in_(order_ids)).all() if order_ids else []
    revenue = round(sum(b.amount or 0 for b in bills), 2)
    paid_total = sum(1 for o in orders if o.order_status in ("paid", "checked_in", "checked_out"))
    today = date.today()
    check_in_today = sum(1 for o in orders if o.check_in == today)

    rooms = db.query(Room).filter(Room.hotel_id == hotel_id).all()
    occupied = sum(1 for r in rooms if r.status == "occupied")
    occupancy = round(occupied / len(rooms) * 100, 2) if rooms else 0

    daily_map = {}
    for b in bills:
        if not b.pay_time:
            continue
        key = b.pay_time.strftime("%Y-%m-%d")
        entry = daily_map.setdefault(key, {"date": key, "orders": 0, "revenue": 0.0})
        entry["orders"] += 1
        entry["revenue"] = round(entry["revenue"] + (b.amount or 0), 2)
    daily = sorted(daily_map.values(), key=lambda x: x["date"], reverse=True)[:7]

    return {
        "hotel_id": hotel_id,
        "hotel_name": hotel.name if hotel else None,
        "order_total": len(orders),
        "paid_total": paid_total,
        "revenue": revenue,
        "check_in_today": check_in_today,
        "occupancy_rate": occupancy,
        "daily": daily,
    }


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), hotel_id: int = Depends(require_merchant_hotel)):
    orders = db.query(HotelOrder).filter(HotelOrder.hotel_id == hotel_id).all()
    rooms = db.query(Room).filter(Room.hotel_id == hotel_id).all()
    return DashboardOut(
        hotel_count=1,
        pending_count=sum(1 for o in orders if o.order_status == "pending_pay"),
        confirm_count=sum(1 for o in orders if o.order_status in ("paid", "checked_in", "checked_out")),
        reject_count=sum(1 for o in orders if o.order_status == "cancelled"),
        booking_total=len(orders),
    )


# ---------------------------------------------------------------------------
# 酒店资料 / 资质认证（v0.16）
# ---------------------------------------------------------------------------

@router.get("/hotel-status")
def my_hotel_status(db: Session = Depends(get_db), shop: User = Depends(require_merchant)):
    """商家顶部提示与客房开关依据。"""
    return hotel_audit_service.merchant_status(db, shop.id, shop)


@router.get("/hotel-profile")
def get_my_hotel_profile(db: Session = Depends(get_db), shop: User = Depends(require_merchant)):
    profile = hotel_audit_service.get_profile(db, shop.id)
    return {
        "profile": hotel_audit_service.serialize_profile(profile),
        "status": hotel_audit_service.merchant_status(db, shop.id, shop),
    }


@router.put("/hotel-profile")
def save_my_hotel_profile(
    payload: HotelProfileUpsert,
    submit: bool = Query(False),
    db: Session = Depends(get_db),
    shop: User = Depends(require_merchant),
):
    try:
        profile = hotel_audit_service.save_profile(db, shop.id, payload.model_dump(), submit=submit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"profile": hotel_audit_service.serialize_profile(profile)}


@router.post("/hotel-profile/reopen")
def reopen_my_hotel_profile(db: Session = Depends(get_db), shop: User = Depends(require_merchant)):
    try:
        hotel_audit_service.reopen(db, shop.id, hotel_audit_service.KIND_PROFILE)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


@router.get("/hotel-cert")
def get_my_hotel_cert(db: Session = Depends(get_db), shop: User = Depends(require_merchant)):
    cert = hotel_audit_service.get_cert(db, shop.id)
    return {"cert": hotel_audit_service.serialize_cert(cert)}


@router.put("/hotel-cert")
def save_my_hotel_cert(
    payload: HotelCertUpsert,
    submit: bool = Query(False),
    db: Session = Depends(get_db),
    shop: User = Depends(require_merchant),
):
    try:
        cert = hotel_audit_service.save_cert(db, shop.id, payload.model_dump(), submit=submit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"cert": hotel_audit_service.serialize_cert(cert)}


@router.post("/hotel-cert/reopen")
def reopen_my_hotel_cert(db: Session = Depends(get_db), shop: User = Depends(require_merchant)):
    try:
        hotel_audit_service.reopen(db, shop.id, hotel_audit_service.KIND_CERT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}
