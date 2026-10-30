from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.database import get_db
from models import User
from schemas.trip import (
    SmartRecommendRequest,
    SmartRecommendResponse,
    TripDetail,
    TripGenerateRequest,
    TripGenerateResponse,
    TripListResponse,
    TripSaveRequest,
)
from services import trip_service

router = APIRouter()


# 注意：静态路径必须定义在 /{trip_id} 之前，否则 "my" / "list" 会被当成 trip_id 匹配

@router.post("/generate", response_model=TripGenerateResponse)
def generate_trip(
    payload: TripGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return trip_service.generate_route(
            db,
            payload.spot_ids,
            payload.start_spot_id,
            payload.days,
            hotel_per_day=payload.hotel_per_day,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/save", response_model=TripDetail)
def save_trip(
    payload: TripSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        trip = trip_service.save_trip(
            db,
            user_id=current_user.id,
            name=payload.name,
            spot_ids=payload.spot_ids,
            start_spot_id=payload.start_spot_id,
            days=payload.days,
            hotel_per_day=payload.hotel_per_day,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return trip_service.build_detail(trip)


@router.post("/smart-recommend", response_model=SmartRecommendResponse)
def smart_recommend(
    payload: SmartRecommendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return trip_service.smart_recommend(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/my", response_model=TripListResponse)
@router.get("/list", response_model=TripListResponse)
def list_my_trips(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return trip_service.get_my_trips(db, current_user.id, page, page_size)


@router.get("/{trip_id}", response_model=TripDetail)
def get_trip_detail(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = trip_service.get_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="路线不存在")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作")
    return trip_service.build_detail(trip)


@router.delete("/{trip_id}")
def delete_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = trip_service.get_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="路线不存在")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作")
    trip_service.delete_trip(db, trip)
    return {"message": "删除成功"}
