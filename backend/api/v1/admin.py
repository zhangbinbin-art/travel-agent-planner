from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.deps import require_admin
from models import Comment, Hotel, HotelBooking, HotelOrder, Post, Room, User
from schemas.post import PostOut, PostListResponse
from schemas.comment import CommentOut
from schemas.admin import PostReview, CommentReview
from schemas.hotel import (
    BookingListResponse,
    HotelCreate,
    HotelListResponse,
    HotelOut,
    HotelStatusUpdate,
    HotelUpdate,
    MerchantAuditUpdate,
    MerchantListResponse,
    MerchantOut,
    OrderListResponse,
)
from pydantic import BaseModel
from typing import Optional
from services import post_service, comment_service
from services.hotel_service import build_booking_out
from services import hotel_audit_service
from schemas.hotel_audit import AuditRejectRequest

router = APIRouter()


@router.get("/post/list", response_model=PostListResponse)
def admin_post_list(
    status: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str = Query(""),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    status_filter = None
    if status != "":
        try:
            s = int(status)
            if s not in (0, 1, 2):
                raise HTTPException(status_code=422, detail="Invalid status")
            status_filter = s
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid status")
    res = post_service.get_posts(db, keyword=keyword, page=page, page_size=page_size, sort="latest", status=status_filter, spot_id=None, current_user=admin)
    return res


@router.put("/post/{post_id}/review", response_model=PostOut)
def admin_review_post(
    post_id: int,
    review: PostReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    post.status = review.status
    post_service.recompute_heat(post)
    db.commit()
    db.refresh(post)
    return post_service.build_post_out(post, db=db, current_user=admin)


@router.get("/comment/list")
def admin_comment_list(
    status: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(Comment)
    if status != "":
        try:
            s = int(status)
            if s in (0, 1, 2):
                query = query.filter(Comment.status == s)
        except Exception:
            pass
    total = query.count()
    comments = query.order_by(Comment.created_at.desc(), Comment.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    user_ids = {c.user_id for c in comments if c.user_id}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    items = [comment_service.build_comment_out(c, users.get(c.user_id), db=db, current_user=admin) for c in comments]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/comment/{comment_id}/review", response_model=CommentOut)
def admin_review_comment(
    comment_id: int,
    review: CommentReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    comment.status = review.status
    db.commit()
    db.refresh(comment)
    return comment_service.build_comment_out(comment, db.query(User).filter(User.id == comment.user_id).first(), db=db, current_user=admin)


@router.get("/hotel", response_model=HotelListResponse)
def admin_hotel_list(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hotels = db.query(Hotel).order_by(Hotel.id.desc()).all()
    return {"items": hotels, "total": len(hotels)}


@router.get("/booking", response_model=BookingListResponse)
def admin_booking_list(
    status: str = Query(""),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(HotelBooking)
    if status:
        query = query.filter(HotelBooking.status == status)
    bookings = query.order_by(HotelBooking.id.desc()).all()

    hotel_ids = {b.hotel_id for b in bookings}
    user_ids = {b.user_id for b in bookings if b.user_id}
    hotel_map = (
        {h.id: h for h in db.query(Hotel).filter(Hotel.id.in_(hotel_ids)).all()}
        if hotel_ids
        else {}
    )
    user_map = (
        {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
        if user_ids
        else {}
    )
    items = [
        build_booking_out(b, hotel_map.get(b.hotel_id), user_map.get(b.user_id))
        for b in bookings
    ]
    return {"items": items, "total": len(items)}


@router.get("/merchant", response_model=MerchantListResponse)
def admin_merchant_list(
    audit_status: str = Query(""),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(User).filter(User.role == "merchant")
    if audit_status:
        query = query.filter(User.audit_status == audit_status)
    users = query.order_by(User.id.desc()).all()
    return {"items": users, "total": len(users)}


@router.put("/merchant/{uid}/audit", response_model=MerchantOut)
def admin_audit_merchant(
    uid: int,
    payload: MerchantAuditUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if payload.audit_status not in ("pending", "approved", "rejected"):
        raise HTTPException(status_code=422, detail="audit_status 只能为 pending/approved/rejected")
    user = db.query(User).filter(User.id == uid, User.role == "merchant").first()
    if not user:
        raise HTTPException(status_code=404, detail="商家不存在")
    user.audit_status = payload.audit_status
    db.commit()
    db.refresh(user)
    return user

# ---------------------------------------------------------------------------
# v0.11 管理员统一维护酒店基础资料
# ---------------------------------------------------------------------------

class MerchantBindRequest(BaseModel):
    hotel_id: Optional[int] = None


def _admin_order_out(order, hotel, room, user):
    days = (order.check_out - order.check_in).days
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
        "days": days if days > 0 else 1,
        "people_count": order.people_count or 1,
        "total_price": order.total_price,
        "pay_channel": order.pay_channel,
        "order_status": order.order_status,
        "create_time": order.create_time,
        "start_date": order.check_in,
        "end_date": order.check_out,
    }


@router.post("/hotel", response_model=HotelOut)
def admin_create_hotel(
    payload: HotelCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hotel = Hotel(status="on_shelf", **payload.model_dump())
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


@router.put("/hotel/{hotel_id}", response_model=HotelOut)
def admin_update_hotel(
    hotel_id: int,
    payload: HotelUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="酒店不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(hotel, key, value)
    db.commit()
    db.refresh(hotel)
    return hotel


@router.put("/hotel/{hotel_id}/status", response_model=HotelOut)
def admin_hotel_status(
    hotel_id: int,
    payload: HotelStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        status = payload.validated()
    except ValueError:
        raise HTTPException(status_code=422, detail="status 只能为 on_shelf 或 off_shelf")
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="酒店不存在")
    hotel.status = status
    db.commit()
    db.refresh(hotel)
    return hotel


@router.delete("/hotel/{hotel_id}")
def admin_delete_hotel(
    hotel_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="酒店不存在")
    if db.query(Room).filter(Room.hotel_id == hotel_id).first() or db.query(HotelOrder).filter(HotelOrder.hotel_id == hotel_id).first():
        raise HTTPException(status_code=400, detail="该酒店已有客房或订单，建议下架而不是删除")
    db.delete(hotel)
    db.commit()
    return {"message": "删除成功"}


@router.get("/order", response_model=OrderListResponse)
def admin_order_list(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    orders = db.query(HotelOrder).order_by(HotelOrder.id.desc()).all()
    hotels = {h.id: h for h in db.query(Hotel).all()}
    rooms = {r.id: r for r in db.query(Room).all()}
    users = {u.id: u for u in db.query(User).all()}
    items = [
        _admin_order_out(o, hotels.get(o.hotel_id), rooms.get(o.room_id), users.get(o.user_id))
        for o in orders
    ]
    return {"items": items, "total": len(items)}


@router.put("/merchant/{uid}/bind", response_model=MerchantOut)
def admin_bind_merchant_hotel(
    uid: int,
    payload: MerchantBindRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == uid, User.role == "merchant").first()
    if not user:
        raise HTTPException(status_code=404, detail="商家不存在")
    if payload.hotel_id is not None:
        hotel = db.query(Hotel).filter(Hotel.id == payload.hotel_id).first()
        if not hotel:
            raise HTTPException(status_code=404, detail="酒店不存在")
        # 双向绑定：酒店记录同步所属商户，保证后端校验一致
        hotel.merchant_id = user.id
    user.merchant_hotel_id = payload.hotel_id
    db.commit()
    db.refresh(user)
    return user

@router.get("/room")
def admin_room_list(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """管理员查看平台全部客房数据。"""
    rows = db.query(Room).order_by(Room.hotel_id.asc(), Room.id.asc()).all()
    hotel_map = {h.id: h.name for h in db.query(Hotel).all()}
    return {
        "items": [
            {
                "id": r.id,
                "hotel_id": r.hotel_id,
                "hotel_name": hotel_map.get(r.hotel_id),
                "room_type": r.room_type,
                "room_price": r.room_price,
                "bed_info": r.bed_info,
                "max_guest": r.max_guest,
                "stock": r.stock,
                "status": r.status,
            }
            for r in rows
        ],
        "total": len(rows),
    }


# ---------------------------------------------------------------------------
# 酒店资料 / 资质审核（v0.16）
# ---------------------------------------------------------------------------

@router.get("/hotel-audits")
def admin_hotel_audits(
    status: str = Query("pending"),
    keyword: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """待审核 / 已通过 / 已驳回 列表；status 传 all 时返回全部。"""
    st = None if status in ("", "all") else status
    return {"items": hotel_audit_service.audit_items(db, status=st, keyword=keyword)}


@router.post("/hotel-audits/{kind}/{item_id}/approve")
def admin_approve_hotel_audit(
    kind: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return hotel_audit_service.approve(db, kind, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/hotel-audits/{kind}/{item_id}/reject")
def admin_reject_hotel_audit(
    kind: str,
    item_id: int,
    payload: AuditRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return hotel_audit_service.reject(db, kind, item_id, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
