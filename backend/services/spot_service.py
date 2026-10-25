from sqlalchemy.orm import Session
from models import Spot
from typing import Optional


def get_spots(db: Session, keyword: Optional[str] = None, page: int = 1, page_size: int = 10):
    query = db.query(Spot)
    if keyword:
        keyword = keyword.strip()
        if keyword:
            query = query.filter(
                (Spot.name.contains(keyword)) | (Spot.city.contains(keyword))
            )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_spot_by_id(db: Session, spot_id: int):
    return db.query(Spot).filter(Spot.id == spot_id).first()


def create_spot(db: Session, spot_data: dict):
    spot = Spot(**spot_data)
    db.add(spot)
    db.commit()
    db.refresh(spot)
    return spot


def update_spot(db: Session, spot: Spot, spot_data: dict):
    for key, value in spot_data.items():
        if value is not None:
            setattr(spot, key, value)
    db.commit()
    db.refresh(spot)
    return spot


def delete_spot(db: Session, spot: Spot):
    db.delete(spot)
    db.commit()
    return spot
