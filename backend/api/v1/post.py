from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.deps import get_current_user
from models import User, Post, Comment
from schemas.post import (
    PostCreate,
    PostUpdate,
    PostOut,
    PostDetailOut,
    PostListResponse,
)
from schemas.comment import CommentCreate, CommentOut
from services import post_service, comment_service
from services import sentiment_service
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError
from core.config import settings

router = APIRouter()

security = HTTPBearer(auto_error=False)


def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user_id_int = int(user_id)
    except (PyJWTError, ValueError, TypeError):
        return None
    user = db.query(User).filter(User.id == user_id_int).first()
    return user


@router.get("/spot/{spot_id}/sentiment")
def spot_sentiment(spot_id: int, db: Session = Depends(get_db)):
    res = sentiment_service.get_spot_sentiment(db, spot_id)
    return res


@router.get("/list", response_model=PostListResponse)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort: str = Query("latest"),
    keyword: str = Query(""),
    status: str = Query(""),
    spot_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    if sort not in ("latest", "hot"):
        sort = "latest"
    status_filter = None
    if current_user is None or getattr(current_user, "role", "user") != "admin":
        status_filter = 1
    else:
        if status != "":
            try:
                s = int(status)
                if s not in (0, 1, 2):
                    raise HTTPException(status_code=422, detail="Invalid status")
                status_filter = s
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid status")
        else:
            status_filter = None
    return post_service.get_posts(
        db,
        keyword=keyword,
        page=page,
        page_size=page_size,
        sort=sort,
        status=status_filter,
        spot_id=spot_id,
        current_user=current_user,
    )


@router.get("/{post_id}", response_model=PostDetailOut)
def get_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_optional)):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    status = getattr(post, "status", 0) or 0
    if status != 1:
        if current_user is None:
            raise HTTPException(status_code=404, detail="游记不存在")
        if getattr(current_user, "role", "user") != "admin" and current_user.id != post.user_id:
            raise HTTPException(status_code=404, detail="游记不存在")
    post.view_count = int(post.view_count or 0) + 1
    post_service.recompute_heat(post)
    db.commit()
    db.refresh(post)
    data = post_service.build_post_out(post, db=db, current_user=current_user)
    comments = comment_service.get_comments_by_post(db, post_id, current_user=current_user)
    if current_user is None:
        comments = [c for c in comments if c.get("status") == 1]
    elif getattr(current_user, "role", "user") == "admin":
        pass
    else:
        filtered = []
        for c in comments:
            if c.get("status") == 1:
                filtered.append(c)
            elif c.get("user_id") == current_user.id:
                filtered.append(c)
            else:
                continue
        comments = filtered
    data["comments"] = comments[:20]
    return data


@router.post("", response_model=PostOut)
@router.post("/", response_model=PostOut)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = post_service.create_post(db, current_user.id, post_in.model_dump())
    return post_service.build_post_out(post, db=db, current_user=current_user)


def _ensure_owner_or_admin(current_user: User, owner_id: int):
    if getattr(current_user, "role", "user") != "admin" and current_user.id != owner_id:
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
    is_admin = getattr(current_user, "role", "user") == "admin"
    post = post_service.update_post(db, post, post_in.model_dump(exclude_unset=True), is_admin=is_admin)
    return post_service.build_post_out(post, db=db, current_user=current_user)


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


@router.post("/{post_id}/like")
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    if getattr(post, "status", 0) != 1:
        raise HTTPException(status_code=400, detail="游记未通过审核")
    res = post_service.toggle_like_post(db, current_user.id, post)
    return res


@router.post("/{post_id}/comment", response_model=CommentOut)
def create_comment_on_post(
    post_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    if getattr(post, "status", 0) != 1:
        raise HTTPException(status_code=400, detail="游记未通过审核")
    comment = comment_service.create_comment(db, user_id=current_user.id, post_id=post_id, content=comment_in.content, score=comment_in.score)
    return comment_service.build_comment_out(comment, current_user, db=db, current_user=current_user)


@router.get("/{post_id}/comment-list")
def comment_list(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    query = db.query(Comment).filter(Comment.post_id == post_id)
    if current_user is None:
        query = query.filter(Comment.status == 1)
    elif getattr(current_user, "role", "user") == "admin":
        if status != "":
            try:
                s = int(status)
                if s in (0, 1, 2):
                    query = query.filter(Comment.status == s)
            except Exception:
                pass
    else:
        from sqlalchemy import or_

        query = query.filter(or_(Comment.status == 1, Comment.user_id == current_user.id))
    total = query.count()
    comments = query.order_by(Comment.created_at.asc(), Comment.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    user_ids = {c.user_id for c in comments if c.user_id}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    items = [comment_service.build_comment_out(c, users.get(c.user_id), db=db, current_user=current_user) for c in comments]
    return {"items": items, "total": total, "page": page, "page_size": page_size}

