from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.deps import get_current_user, get_optional_user
from models import User, Post, Comment, PostFavorite
from schemas.post import (
    PostCreate,
    PostUpdate,
    PostVisibilityUpdate,
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
    current_user: User = Depends(get_optional_user),
):
    if sort not in ("latest", "hot"):
        sort = "latest"
    viewer_role = getattr(current_user, "role", "user") if current_user else "guest"
    status_filter = None
    if viewer_role != "admin":
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
    # 广场列表（未指定景点）不展示测试用的「点评合集」帖，避免污染游记广场；
    # 景点详情按 spot_id 查询时仍会返回，保证点评区与情感统计正常。
    title_filter = None
    if spot_id is None:
        title_filter = ~Post.title.like("【游客点评】%")
    return post_service.get_posts(
        db,
        keyword=keyword,
        title_filter=title_filter,
        page=page,
        page_size=page_size,
        sort=sort,
        status=status_filter,
        spot_id=spot_id,
        current_user=current_user,
        viewer_id=getattr(current_user, "id", None),
        include_all_visibility=viewer_role == "admin",
    )


@router.get("/my", response_model=PostListResponse)
def list_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户自己的游记列表（含待审核、已驳回），用于个人中心「我的帖子」。"""
    return post_service.get_user_posts(
        db,
        current_user.id,
        page=page,
        page_size=page_size,
        current_user=current_user,
    )


@router.get("/{post_id}", response_model=PostDetailOut)
def get_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    # 拉黑拦截：作者把我拉黑后，直链也不能看
    from services import block_service

    if block_service.is_blocked(db, post.user_id, getattr(current_user, "id", None)):
        raise HTTPException(status_code=404, detail="游记不存在")
    status = getattr(post, "status", 0) or 0
    if status != 1:
        if getattr(current_user, "role", "user") != "admin" and current_user.id != post.user_id:
            raise HTTPException(status_code=404, detail="游记不存在")
    # 可见范围拦截：非公开游记仅作者本人与管理员可访问
    visible = getattr(post, "visible", "public") or "public"
    if visible != "public":
        if getattr(current_user, "role", "user") != "admin" and current_user.id != post.user_id:
            raise HTTPException(status_code=404, detail="游记不存在")
    post.view_count = int(post.view_count or 0) + 1
    post_service.recompute_heat(post)
    db.commit()
    db.refresh(post)
    data = post_service.build_post_out(post, db=db, current_user=current_user)
    comments = comment_service.get_comments_by_post(db, post_id, current_user=current_user)
    if getattr(current_user, "role", "user") == "admin":
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


@router.put("/{post_id}/visible", response_model=PostOut)
def update_post_visibility(
    post_id: int,
    payload: PostVisibilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改游记可见范围（public/friend/private）。只改可见性，不重置审核状态。"""
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    if current_user.id != post.user_id and getattr(current_user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="只有作者本人可以修改可见范围")
    post.visible = payload.visible
    db.commit()
    db.refresh(post)
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


@router.post("/{post_id}/favorite")
def toggle_post_favorite(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    existing = (
        db.query(PostFavorite)
        .filter(PostFavorite.user_id == current_user.id, PostFavorite.post_id == post_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        favorited = False
        message = "已取消收藏"
    else:
        try:
            db.add(PostFavorite(user_id=current_user.id, post_id=post_id))
            db.commit()
            favorited = True
            message = "收藏成功"
        except Exception:
            db.rollback()
            favorited = (
                db.query(PostFavorite)
                .filter(PostFavorite.user_id == current_user.id, PostFavorite.post_id == post_id)
                .first()
                is not None
            )
            message = "收藏成功" if favorited else "已取消收藏"
    favorite_count = db.query(PostFavorite).filter(PostFavorite.post_id == post_id).count()
    return {
        "favorited": favorited,
        "post_id": post_id,
        "favorite_count": favorite_count,
        "message": message,
    }


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
    current_user: User = Depends(get_current_user),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    query = db.query(Comment).filter(Comment.post_id == post_id)
    if getattr(current_user, "role", "user") == "admin":
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

