from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.deps import require_admin
from models import Post, Comment, User
from schemas.post import PostOut, PostListResponse
from schemas.comment import CommentOut
from schemas.admin import PostReview, CommentReview
from services import post_service, comment_service

router = APIRouter()


@router.get("/post/list", response_model=PostListResponse)
def admin_post_list(
    status: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str = Query(""),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    status_filter = None
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
    res = post_service.get_posts(db, keyword=keyword, page=page, page_size=page_size, sort="latest", status=status_filter, spot_id=None, current_user=admin)
    return res


@router.put("/post/{post_id}/review", response_model=PostOut)
def admin_review_post(
    post_id: int,
    review: PostReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    post = post_service.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    post.status = review.status
    post_service.recompute_heat(post)
    db.commit()
    db.refresh(post)
    return post_service.build_post_out(post, db=db, current_user=admin)


@router.get("/comment/list")
def admin_comment_list(
    status: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(Comment)
    if status != "":
        try:
            s = int(status)
            if s in (0, 1, 2):
                query = query.filter(Comment.status == s)
        except Exception:
            pass
    total = query.count()
    comments = query.order_by(Comment.created_at.desc(), Comment.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    user_ids = {c.user_id for c in comments if c.user_id}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    items = [comment_service.build_comment_out(c, users.get(c.user_id), db=db, current_user=admin) for c in comments]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/comment/{comment_id}/review", response_model=CommentOut)
def admin_review_comment(
    comment_id: int,
    review: CommentReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    comment.status = review.status
    db.commit()
    db.refresh(comment)
    return comment_service.build_comment_out(comment, db.query(User).filter(User.id == comment.user_id).first(), db=db, current_user=admin)
