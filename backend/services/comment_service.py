from sqlalchemy.orm import Session
from models import Comment, User, CommentLike, Post
from typing import Optional


STATUS_TEXT = {0: "待审核", 1: "已通过", 2: "已驳回"}


def build_comment_out(comment: Comment, author: Optional[User] = None, db: Session = None, current_user: User = None) -> dict:
    liked = False
    if db is not None and current_user is not None and getattr(current_user, "id", None):
        liked = db.query(CommentLike).filter(CommentLike.user_id == current_user.id, CommentLike.comment_id == comment.id).first() is not None
    status = getattr(comment, "status", 0) or 0
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "score": getattr(comment, "score", 5) or 5,
        "like_count": int(getattr(comment, "like_count", 0) or 0),
        "liked": bool(liked),
        "status": status,
        "status_text": STATUS_TEXT.get(status, str(status)),
        "created_at": getattr(comment, "created_at", None),
        "author": (
            {"id": author.id, "username": author.username, "role": author.role}
            if author
            else None
        ),
    }


def get_comments_by_post(db: Session, post_id: int, current_user: User = None):
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )
    user_ids = {c.user_id for c in comments if c.user_id}
    users = {}
    if user_ids:
        users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    return [build_comment_out(c, users.get(c.user_id), db=db, current_user=current_user) for c in comments]


def get_comment_by_id(db: Session, comment_id: int):
    return db.query(Comment).filter(Comment.id == comment_id).first()


def create_comment(db: Session, user_id: int, post_id: int = None, content: str = None, score: int = 5, spot_id: int = None):
    comment = Comment(
        user_id=user_id,
        post_id=post_id,
        spot_id=spot_id,
        content=content,
        score=score,
        status=0,
        like_count=0,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    # update post counts if post_id
    if post_id:
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.comment_count = int(post.comment_count or 0) + 1
            from services import post_service

            post_service.recompute_heat(post)
            db.commit()
    return comment


def delete_comment(db: Session, comment: Comment):
    post_id = comment.post_id
    db.query(CommentLike).filter(CommentLike.comment_id == comment.id).delete(synchronize_session=False)
    db.delete(comment)
    db.commit()
    if post_id:
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.comment_count = max(0, int(post.comment_count or 0) - 1)
            from services import post_service

            post_service.recompute_heat(post)
            db.commit()
    return comment


def toggle_like_comment(db: Session, user_id: int, comment: Comment):
    existing = db.query(CommentLike).filter(CommentLike.user_id == user_id, CommentLike.comment_id == comment.id).first()
    if existing:
        db.delete(existing)
        comment.like_count = max(0, int(comment.like_count or 0) - 1)
        liked = False
    else:
        like = CommentLike(user_id=user_id, comment_id=comment.id)
        db.add(like)
        comment.like_count = int(comment.like_count or 0) + 1
        liked = True
    db.commit()
    db.refresh(comment)
    return {"liked": liked, "like_count": int(comment.like_count or 0)}

