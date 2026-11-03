"""酒店资料 / 资质认证的请求结构。"""

from typing import List, Optional

from pydantic import BaseModel, Field


class HotelProfileUpsert(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    address: Optional[str] = Field(None, max_length=255)
    lng: Optional[float] = None
    lat: Optional[float] = None
    phone: Optional[str] = Field(None, max_length=30)
    intro: Optional[str] = None
    imgs: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    checkin_rule: Optional[str] = Field(None, max_length=255)


class HotelCertUpsert(BaseModel):
    hotel_full_name: Optional[str] = Field(None, max_length=150)
    credit_code: Optional[str] = Field(None, max_length=50)
    legal_name: Optional[str] = Field(None, max_length=50)
    legal_phone: Optional[str] = Field(None, max_length=30)
    license_img: Optional[str] = None
    id_card_imgs: List[str] = Field(default_factory=list)


class AuditRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=255)
