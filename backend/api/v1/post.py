from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.deps import get_current_user
from models import User
from schemas.post import (
    PostCreate,
    PostUpdate,
    PostOut,
    PostDetailOut,
    PostListResponse,
)
from services import post_service, comment_service

router = APIRouter()


@router.get("/list", response_model=PostListResponse)
def list_posts(
    keyword: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return post_service.get_posts(db, keyword=keyword, page=page, page_size=page_size)


@router.get("/{post_id}", response_model=PostDetailOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    data = post_service.build_post_out(post)
    data["comments"] = comment_service.get_comments_by_post(db, post_id)
    return data


@router.post("", response_model=PostOut)
@router.post("/", response_model=PostOut)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = post_service.create_post(db, current_user.id, post_in.model_dump())
    return post_service.build_post_out(post)


def _ensure_owner_or_admin(current_user: User, owner_id: int):
    if current_user.role != "admin" and current_user.id != owner_id:
        raise HTTPException(status_code=403, detail="无权限操作")


@router.put("/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    post_in: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    _ensure_owner_or_admin(current_user, post.user_id)
    post = post_service.update_post(db, post, post_in.model_dump(exclude_unset=True))
    return post_service.build_post_out(post)


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    _ensure_owner_or_admin(current_user, post.user_id)
    post_service.delete_post(db, post)
    return {"message": "删除成功"}
