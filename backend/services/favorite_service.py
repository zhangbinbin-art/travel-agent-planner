from sqlalchemy.orm import Session
from models import Favorite, Spot
from typing import List, Optional


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


def is_favorited(db: Session, user_id: int, spot_id: int) -> bool:
    """判断当前用户是否已收藏指定景点。"""
    return (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.spot_id == spot_id)
        .first()
        is not None
    )


def toggle_favorite(db: Session, user_id: int, spot_id: int) -> dict:
    """切换收藏状态：已收藏则取消，未收藏则新增。

    返回 {"favorited": bool, "favorite_id": Optional[int]}；
    取消收藏时 favorite_id 为 None。
    """
    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.spot_id == spot_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        return {"favorited": False, "favorite_id": None}

    fav = Favorite(user_id=user_id, spot_id=spot_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return {"favorited": True, "favorite_id": fav.id}


def get_user_favorite_spots(db: Session, user_id: int) -> List[Favorite]:
    """返回当前用户的全部收藏景点，按收藏时间倒序（同一时间按 id 倒序）。

    不做分页，供“我的收藏景点”聚合接口一次返回完整列表。
    """
    return (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc(), Favorite.id.desc())
        .all()
    )
