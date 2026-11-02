from fastapi import APIRouter, Depends, HTTPException

from api.deps import require_any_auth
from models import User
from schemas.map import GeoCodeRequest, GeoCodeResponse
from services import geo_service

router = APIRouter()


@router.post(
    "/geo-code",
    response_model=GeoCodeResponse,
    summary="地点名称转经纬度（高德 Web 服务地理编码）",
)
def geo_code(
    payload: GeoCodeRequest,
    current_user: User = Depends(require_any_auth),
):
    """后台录入景点/酒店时按名称一键取经纬度，避免手填坐标出错。"""
    try:
        return geo_service.geocode(payload.location_name, payload.city)
    except geo_service.GeoCodeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
