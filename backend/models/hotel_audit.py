"""商家酒店资料 / 资质认证（与客户端 hotels 表分离，审核通过后才同步对外展示）。"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from core.database import Base

# 审核状态：draft 草稿 / pending 待审核 / approved 通过 / rejected 驳回
STATUS_DRAFT = "draft"
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


class HotelProfile(Base):
    """酒店资料（名称/地址/简介/相册/标签/入住规则）。"""

    __tablename__ = "hotel_profiles"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False, default="")
    address = Column(String(255), nullable=True)
    lng = Column(String(30), nullable=True)
    lat = Column(String(30), nullable=True)
    phone = Column(String(30), nullable=True)
    # 酒店基础房价（元/天），审核通过后同步到 hotels.price_per_day
    price = Column(Float, default=300)
    intro = Column(Text, nullable=True)
    # 相册图片 JSON 数组
    imgs = Column(Text, nullable=True)
    # 标签 JSON 数组
    tags = Column(Text, nullable=True)
    checkin_rule = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default=STATUS_DRAFT, index=True)
    audit_msg = Column(String(255), nullable=True)
    submit_time = Column(DateTime(timezone=True), nullable=True)
    audit_time = Column(DateTime(timezone=True), nullable=True)
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HotelCertification(Base):
    """酒店资质认证（营业执照 / 法人信息）。"""

    __tablename__ = "hotel_certifications"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    hotel_full_name = Column(String(150), nullable=True)
    credit_code = Column(String(50), nullable=True)
    legal_name = Column(String(50), nullable=True)
    legal_phone = Column(String(30), nullable=True)
    license_img = Column(Text, nullable=True)
    # 身份证正反面 JSON 数组（2 张）
    id_card_imgs = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default=STATUS_DRAFT, index=True)
    audit_msg = Column(String(255), nullable=True)
    submit_time = Column(DateTime(timezone=True), nullable=True)
    audit_time = Column(DateTime(timezone=True), nullable=True)
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
