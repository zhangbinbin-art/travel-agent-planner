from pydantic import BaseModel, Field
from typing import Optional


class GeoCodeRequest(BaseModel):
    """地点名称 -> 经纬度。"""

    location_name: str = Field(..., min_length=1, max_length=100)
    # 可选：限定城市，减少重名地点误判
    city: Optional[str] = Field(None, max_length=50)


class GeoCodeResponse(BaseModel):
    location_name: str
    lng: float
    lat: float
    formatted_address: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    level: Optional[str] = None
