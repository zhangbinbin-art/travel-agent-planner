from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.deps import get_current_user, require_admin
from models import User, Spot
from schemas.spot import SpotCreate, SpotUpdate, SpotOut, SpotListResponse
from services import spot_service

router = APIRouter()


@router.get("/list", response_model=SpotListResponse)
def list_spots(
    keyword: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    result = spot_service.get_spots(db, keyword=keyword, page=page, page_size=page_size)
    return result


@router.get("/{spot_id}", response_model=SpotOut)
def get_spot(spot_id: int, db: Session = Depends(get_db)):
    spot = spot_service.get_spot_by_id(db, spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    return spot


@router.post("", response_model=SpotOut)
@router.post("/", response_model=SpotOut)
def create_spot(
    spot_in: SpotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    spot = spot_service.create_spot(db, spot_in.model_dump())
    return spot


@router.put("/{spot_id}", response_model=SpotOut)
def update_spot(
    spot_id: int,
    spot_in: SpotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    spot = spot_service.get_spot_by_id(db, spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    spot = spot_service.update_spot(db, spot, spot_in.model_dump(exclude_unset=True))
    return spot


@router.delete("/{spot_id}")
def delete_spot(
    spot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    spot = spot_service.get_spot_by_id(db, spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    spot_service.delete_spot(db, spot)
    return {"message": "删除成功"}
