from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean, UniqueConstraint, Date
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # user/merchant/admin
    # 商家审核状态：pending（待审核）/ approved（已通过）/ rejected（驳回）
    # 普通用户与管理员不参与商家审核，默认 approved
    audit_status = Column(String(20), default="approved")
    shop_name = Column(String(100), nullable=True)
    # 实名认证（仅模拟校验，不调用公安接口）
    is_real_name_auth = Column(Boolean, default=False)
    real_name = Column(String(50), nullable=True)
    id_card = Column(String(30), nullable=True)
    # 商户绑定的唯一酒店（一个商户账号只管理一家酒店）
    merchant_hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=True)
    email = Column(String(100), unique=True)
    # 注册手机号（用户/商家注册必填）
    phone = Column(String(20), index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Spot(Base):
    __tablename__ = "spots"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(50))
    province = Column(String(50), nullable=True)
    theme = Column(String(50), nullable=True)
    tags = Column(String(255))
    description = Column(Text)
    score = Column(Float, default=0)
    price = Column(Float, nullable=True, default=0)
    cover = Column(String(255), nullable=True)
    # v0.18 批量导入补充字段
    address = Column(String(255), nullable=True)
    heat = Column(Integer, default=0)
    # 经纬度用双精度：MySQL 下 Float 为 4 字节单精度，会丢失 1e-4 量级（约 10m）
    lat = Column(Float(53), nullable=True)
    lng = Column(Float(53), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(150), nullable=False)
    content = Column(Text)
    cover = Column(String(255))
    images = Column(Text, default="[]")
    custom_spots = Column(Text, default="[]")
    spot_ids = Column(Text, default="[]")
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    heat = Column(Integer, default=0)
    status = Column(Integer, default=0)
    visible = Column(String(16), nullable=False, default="public", server_default="public")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    author = relationship("User")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    spot_id = Column(Integer, ForeignKey("spots.id"), nullable=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    content = Column(Text)
    sentiment = Column(String(20))  # positive/neutral/negative
    score = Column(Integer, default=5)
    like_count = Column(Integer, default=0)
    status = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PostLike(Base):
    __tablename__ = "post_likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_post_like_user_post"),)


class CommentLike(Base):
    __tablename__ = "comment_likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    comment_id = Column(Integer, ForeignKey("comments.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="uq_comment_like_user_comment"),)

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    spot_id = Column(Integer, ForeignKey("spots.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    spot = relationship("Spot")
    __table_args__ = (UniqueConstraint("user_id", "spot_id", name="uq_favorite_user_spot"),)

class PostFavorite(Base):
    __tablename__ = "post_favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_post_favorite_user_post"),)

class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(150), nullable=False)
    route_json = Column(Text)  # JSON string: {"spot_ids": [...], "start_spot_id": n, "route": [...], "legs": [...]}
    total_distance = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    author = relationship("User")


class Hotel(Base):
    __tablename__ = "hotels"
    id = Column(Integer, primary_key=True, index=True)
    # 酒店基础资料由管理员维护，允许先建酒店后绑定商户
    merchant_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(150), nullable=False)
    address = Column(String(255))
    lat = Column(Float(53), nullable=True)
    lng = Column(Float(53), nullable=True)
    price_per_day = Column(Float, default=0)
    # 封面图支持链接或本地上传后的 base64，MySQL 需 MEDIUMTEXT 容纳
    cover_img = Column(Text().with_variant(MEDIUMTEXT, "mysql"))
    description = Column(Text)
    facilities = Column(Text)          # 配套设施，逗号分隔
    env_score = Column(Float, default=0)      # 环境评分
    service_score = Column(Float, default=0)  # 服务评分
    # v0.16 商家提交并审核通过后同步的资料字段
    phone = Column(String(30), nullable=True)
    imgs = Column(Text, nullable=True)                 # 相册 JSON 数组
    checkin_rule = Column(String(255), nullable=True)
    status = Column(String(20), default="on_shelf")  # on_shelf / off_shelf
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    merchant = relationship("User", foreign_keys=[merchant_id])


class HotelBooking(Base):
    __tablename__ = "hotel_bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Integer, default=1)
    total_price = Column(Float, default=0)
    status = Column(String(20), default="pending")  # pending / confirm / reject
    guest_count = Column(Integer, default=1)        # 入住人数
    remark = Column(String(500))                    # 备注
    # 关联路线方案（可为空：单独预订酒店）
    route_id = Column(Integer, ForeignKey("trips.id"), nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User")
    hotel = relationship("Hotel")


class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False, index=True)
    room_type = Column(String(100), nullable=False)
    room_price = Column(Float, default=0)
    bed_info = Column(String(100))
    max_guest = Column(Integer, default=2)
    stock = Column(Integer, default=10)
    # 房型图片（链接或上传后的 base64），允许为空
    image_url = Column(Text().with_variant(MEDIUMTEXT, "mysql"), nullable=True)
    # free / occupied / cleaning / maintenance
    status = Column(String(20), default="free")
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    hotel = relationship("Hotel")


class HotelOrder(Base):
    __tablename__ = "hotel_orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    people_count = Column(Integer, default=1)
    total_price = Column(Float, default=0)
    pay_channel = Column(String(20))
    # pending_pay / paid / checked_in / checked_out / cancelled
    order_status = Column(String(20), default="pending_pay")
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User")
    hotel = relationship("Hotel")
    room = relationship("Room")


class GuestRecord(Base):
    __tablename__ = "guest_records"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("hotel_orders.id"), nullable=False, index=True)
    real_name = Column(String(50), nullable=False)
    id_card = Column(String(30))
    checkin_time = Column(DateTime(timezone=True), server_default=func.now())
    order = relationship("HotelOrder")


class Bill(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("hotel_orders.id"), nullable=False, index=True)
    amount = Column(Float, default=0)
    pay_channel = Column(String(20))
    pay_time = Column(DateTime(timezone=True), server_default=func.now())
    order = relationship("HotelOrder")


# 社交模块单独成文件，在此导入以保证 Base.metadata 能收集到这两张表
from models.follow import Follow  # noqa: E402,F401
from models.message import Message  # noqa: E402,F401
from models.block import UserBlock  # noqa: E402,F401
from models.hotel_audit import HotelCertification, HotelProfile  # noqa: E402,F401
