"""酒店资料 / 资质审核服务：草稿保存、提交、管理员审核、审核通过后同步到客户端 hotels 表。"""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from models import Hotel, HotelCertification, HotelProfile, User
from models.hotel_audit import (
    STATUS_APPROVED,
    STATUS_DRAFT,
    STATUS_PENDING,
    STATUS_REJECTED,
)

EDITABLE_STATUS = (STATUS_DRAFT, STATUS_REJECTED)

KIND_PROFILE = "profile"
KIND_CERT = "cert"


def _loads(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        data = json.loads(value)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _dumps(values) -> str:
    return json.dumps(list(values or []), ensure_ascii=False)


def _to_float(value) -> Optional[float]:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num


def serialize_profile(profile: Optional[HotelProfile]) -> Optional[dict]:
    if not profile:
        return None
    return {
        "id": profile.id,
        "shop_id": profile.shop_id,
        "name": profile.name or "",
        "address": profile.address or "",
        "lng": _to_float(profile.lng),
        "lat": _to_float(profile.lat),
        "phone": profile.phone or "",
        "intro": profile.intro or "",
        "imgs": _loads(profile.imgs),
        "tags": _loads(profile.tags),
        "checkin_rule": profile.checkin_rule or "",
        "status": profile.status or STATUS_DRAFT,
        "audit_msg": profile.audit_msg or "",
        "submit_time": profile.submit_time,
        "audit_time": profile.audit_time,
    }


def serialize_cert(cert: Optional[HotelCertification]) -> Optional[dict]:
    if not cert:
        return None
    return {
        "id": cert.id,
        "shop_id": cert.shop_id,
        "hotel_full_name": cert.hotel_full_name or "",
        "credit_code": cert.credit_code or "",
        "legal_name": cert.legal_name or "",
        "legal_phone": cert.legal_phone or "",
        "license_img": cert.license_img or "",
        "id_card_imgs": _loads(cert.id_card_imgs),
        "status": cert.status or STATUS_DRAFT,
        "audit_msg": cert.audit_msg or "",
        "submit_time": cert.submit_time,
        "audit_time": cert.audit_time,
    }


def get_profile(db: Session, shop_id: int) -> Optional[HotelProfile]:
    return db.query(HotelProfile).filter(HotelProfile.shop_id == shop_id).first()


def get_cert(db: Session, shop_id: int) -> Optional[HotelCertification]:
    return db.query(HotelCertification).filter(HotelCertification.shop_id == shop_id).first()


def _ensure_editable(item, kind: str) -> None:
    status = getattr(item, "status", STATUS_DRAFT) if item else STATUS_DRAFT
    if status == STATUS_PENDING:
        raise ValueError("资料正在等待管理员审核，暂不可修改")
    if status == STATUS_APPROVED:
        raise ValueError("资料已审核通过并锁定，如需修改请先申请修改")


def save_profile(db: Session, shop_id: int, data: dict, submit: bool = False) -> HotelProfile:
    profile = get_profile(db, shop_id)
    if profile:
        _ensure_editable(profile, KIND_PROFILE)
    else:
        profile = HotelProfile(shop_id=shop_id, status=STATUS_DRAFT)
        db.add(profile)

    profile.name = (data.get("name") or "").strip()
    if not profile.name:
        raise ValueError("请填写酒店名称")
    profile.address = (data.get("address") or "").strip() or None
    profile.lng = data.get("lng")
    profile.lat = data.get("lat")
    profile.phone = (data.get("phone") or "").strip() or None
    profile.intro = data.get("intro") or None
    profile.imgs = _dumps(data.get("imgs") or [])
    profile.tags = _dumps(data.get("tags") or [])
    profile.checkin_rule = (data.get("checkin_rule") or "").strip() or None
    if submit:
        profile.status = STATUS_PENDING
        profile.audit_msg = None
        profile.submit_time = datetime.now()
    else:
        profile.status = STATUS_DRAFT if profile.status in EDITABLE_STATUS else profile.status
    db.commit()
    db.refresh(profile)
    return profile


def save_cert(db: Session, shop_id: int, data: dict, submit: bool = False) -> HotelCertification:
    cert = get_cert(db, shop_id)
    if cert:
        _ensure_editable(cert, KIND_CERT)
    else:
        cert = HotelCertification(shop_id=shop_id, status=STATUS_DRAFT)
        db.add(cert)

    cert.hotel_full_name = (data.get("hotel_full_name") or "").strip() or None
    cert.credit_code = (data.get("credit_code") or "").strip().upper() or None
    cert.legal_name = (data.get("legal_name") or "").strip() or None
    cert.legal_phone = (data.get("legal_phone") or "").strip() or None
    cert.license_img = data.get("license_img") or None
    cert.id_card_imgs = _dumps(data.get("id_card_imgs") or [])
    if submit:
        if not cert.hotel_full_name or not cert.credit_code:
            raise ValueError("请填写酒店全称与统一社会信用代码")
        if not cert.license_img:
            raise ValueError("请上传营业执照图片")
        cert.status = STATUS_PENDING
        cert.audit_msg = None
        cert.submit_time = datetime.now()
    else:
        cert.status = STATUS_DRAFT if cert.status in EDITABLE_STATUS else cert.status
    db.commit()
    db.refresh(cert)
    return cert


def reopen(db: Session, shop_id: int, kind: str) -> None:
    item = get_profile(db, shop_id) if kind == KIND_PROFILE else get_cert(db, shop_id)
    if not item:
        raise ValueError("尚未提交过资料")
    if item.status != STATUS_APPROVED:
        raise ValueError("只有审核通过的资料才需要申请修改")
    item.status = STATUS_DRAFT
    item.audit_msg = "商家申请修改，请重新提交审核"
    db.commit()


def sync_hotel(db: Session, shop_id: int) -> Optional[Hotel]:
    """资料 + 资质都通过后：写入/更新客户端酒店并上架；否则下架。"""
    profile = get_profile(db, shop_id)
    cert = get_cert(db, shop_id)
    shop = db.query(User).filter(User.id == shop_id).first()
    if not shop:
        return None

    hotel = None
    if shop.merchant_hotel_id:
        hotel = db.query(Hotel).filter(Hotel.id == shop.merchant_hotel_id).first()

    both_ok = bool(
        profile and profile.status == STATUS_APPROVED
        and cert and cert.status == STATUS_APPROVED
    )

    if not hotel and profile and both_ok:
        # 优先复用「同一名称且未绑定商户」的历史酒店，避免客户端出现同名两条
        hotel = (
            db.query(Hotel)
            .filter(Hotel.name == profile.name, Hotel.merchant_id.is_(None))
            .order_by(Hotel.id.asc())
            .first()
        )
    if not hotel and profile and both_ok:
        # 没有可复用的历史酒店时，审核通过后自动创建并绑定
        hotel = Hotel(name=profile.name, status="off_shelf", merchant_id=shop_id, price_per_day=300)
        db.add(hotel)
        db.flush()
        shop.merchant_hotel_id = hotel.id

    if hotel:
        hotel.merchant_id = shop_id
        if profile:
            hotel.name = profile.name or hotel.name
            hotel.address = profile.address
            hotel.lng = _to_float(profile.lng)
            hotel.lat = _to_float(profile.lat)
            hotel.description = profile.intro
            hotel.facilities = ",".join(_loads(profile.tags))
            hotel.phone = profile.phone
            hotel.imgs = profile.imgs
            hotel.checkin_rule = profile.checkin_rule
            imgs = _loads(profile.imgs)
            if imgs:
                hotel.cover_img = imgs[0]
        hotel.status = "on_shelf" if both_ok else "off_shelf"

    db.commit()
    if hotel:
        db.refresh(hotel)
    return hotel


def merchant_status(db: Session, shop_id: int, shop: User) -> dict:
    profile = get_profile(db, shop_id)
    cert = get_cert(db, shop_id)
    p_status = profile.status if profile else None
    c_status = cert.status if cert else None
    verified = p_status == STATUS_APPROVED and c_status == STATUS_APPROVED
    return {
        "profile_status": p_status,
        "cert_status": c_status,
        "profile_msg": (profile.audit_msg if profile else None) or "",
        "cert_msg": (cert.audit_msg if cert else None) or "",
        "verified": verified,
        "hotel_id": shop.merchant_hotel_id,
    }


def audit_items(db: Session, status: Optional[str] = None, keyword: str = "") -> list:
    items = []
    profiles = db.query(HotelProfile).all()
    certs = db.query(HotelCertification).all()
    shops = {u.id: u for u in db.query(User).all()}

    for p in profiles:
        if status and p.status != status:
            continue
        shop = shops.get(p.shop_id)
        items.append(
            {
                "kind": KIND_PROFILE,
                "id": p.id,
                "shop_id": p.shop_id,
                "username": getattr(shop, "username", None),
                "phone": getattr(shop, "phone", None),
                "hotel_name": p.name,
                "status": p.status,
                "audit_msg": p.audit_msg,
                "submit_time": p.submit_time,
                "payload": serialize_profile(p),
            }
        )

    for c in certs:
        if status and c.status != status:
            continue
        shop = shops.get(c.shop_id)
        items.append(
            {
                "kind": KIND_CERT,
                "id": c.id,
                "shop_id": c.shop_id,
                "username": getattr(shop, "username", None),
                "phone": getattr(shop, "phone", None),
                "hotel_name": c.hotel_full_name,
                "status": c.status,
                "audit_msg": c.audit_msg,
                "submit_time": c.submit_time,
                "payload": serialize_cert(c),
            }
        )

    kw = (keyword or "").strip().lower()
    if kw:
        items = [
            i
            for i in items
            if kw in str(i.get("hotel_name") or "").lower()
            or kw in str(i.get("username") or "").lower()
            or kw in str(i.get("phone") or "").lower()
        ]

    items.sort(key=lambda i: (i.get("submit_time") is None, i.get("submit_time") or datetime.min), reverse=False)
    return items


def _get_item(db: Session, kind: str, item_id: int):
    if kind == KIND_PROFILE:
        return db.query(HotelProfile).filter(HotelProfile.id == item_id).first()
    if kind == KIND_CERT:
        return db.query(HotelCertification).filter(HotelCertification.id == item_id).first()
    raise ValueError("未知的审核类型")


def approve(db: Session, kind: str, item_id: int) -> dict:
    item = _get_item(db, kind, item_id)
    if not item:
        raise ValueError("记录不存在")
    if item.status != STATUS_PENDING:
        raise ValueError("只有待审核的记录可以审核")
    item.status = STATUS_APPROVED
    item.audit_msg = None
    item.audit_time = datetime.now()
    db.commit()
    sync_hotel(db, item.shop_id)
    return {"shop_id": item.shop_id, "status": item.status}


def reject(db: Session, kind: str, item_id: int, reason: str) -> dict:
    item = _get_item(db, kind, item_id)
    if not item:
        raise ValueError("记录不存在")
    if item.status != STATUS_PENDING:
        raise ValueError("只有待审核的记录可以审核")
    item.status = STATUS_REJECTED
    item.audit_msg = (reason or "").strip() or "资料不符合要求，请修改后重新提交"
    item.audit_time = datetime.now()
    db.commit()
    sync_hotel(db, item.shop_id)
    return {"shop_id": item.shop_id, "status": item.status}
