from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.deps import get_current_user
from models import User, Spot
from schemas.favorite import FavoriteOut, FavoriteListResponse
from services import favorite_service

router = APIRouter()


@router.post("")
@router.post("/")
def add_favorite(
    spot_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")
    fav = favorite_service.add_favorite(db, current_user.id, spot_id)
    return {"message": "收藏成功", "id": fav.id}


@router.delete("")
@router.delete("/")
def remove_favorite(
    spot_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    favorite_service.remove_favorite(db, current_user.id, spot_id)
    return {"message": "取消收藏成功"}


@router.get("/my", response_model=FavoriteListResponse)
def my_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = favorite_service.get_user_favorites(db, current_user.id, page=page, page_size=page_size)
    return result
