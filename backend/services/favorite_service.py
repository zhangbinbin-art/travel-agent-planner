from sqlalchemy.orm import Session
from models import Favorite, Spot
from typing import Optional


def add_favorite(db: Session, user_id: int, spot_id: int):
    existing = db.query(Favorite).filter(
        Favorite.user_id == user_id, Favorite.spot_id == spot_id
    ).first()
    if existing:
        return existing
    fav = Favorite(user_id=user_id, spot_id=spot_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def remove_favorite(db: Session, user_id: int, spot_id: int):
    fav = db.query(Favorite).filter(
        Favorite.user_id == user_id, Favorite.spot_id == spot_id
    ).first()
    if fav:
        db.delete(fav)
        db.commit()
    return fav


def get_user_favorites(db: Session, user_id: int, page: int = 1, page_size: int = 10):
    query = db.query(Favorite).filter(Favorite.user_id == user_id)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}
