from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core.database import get_db
from api.deps import get_current_user
from models import User, Post
from schemas.comment import CommentCreate, CommentOut
from services import comment_service

router = APIRouter()


@router.post("", response_model=CommentOut)
@router.post("/", response_model=CommentOut)
def create_comment(
    comment_in: CommentCreate,
    post_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="游记不存在")
    comment = comment_service.create_comment(
        db,
        user_id=current_user.id,
        post_id=post_id,
        content=comment_in.content,
        score=comment_in.score,
    )
    post.heat = (post.heat or 0) + 1
    db.commit()
    return comment_service.build_comment_out(comment, current_user)


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    if current_user.role != "admin" and current_user.id != comment.user_id:
        raise HTTPException(status_code=403, detail="无权限操作")
    comment_service.delete_comment(db, comment)
    return {"message": "删除成功"}
