from sqlalchemy.orm import Session
from models import Comment, User
from typing import Optional


def build_comment_out(comment: Comment, author: Optional[User] = None) -> dict:
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "score": comment.score,
        "created_at": comment.created_at,
        "author": (
            {"id": author.id, "username": author.username, "role": author.role}
            if author
            else None
        ),
    }


def get_comments_by_post(db: Session, post_id: int):
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )
    user_ids = {c.user_id for c in comments if c.user_id}
    users = {}
    if user_ids:
        users = {
            u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()
        }
    return [build_comment_out(c, users.get(c.user_id)) for c in comments]


def get_comment_by_id(db: Session, comment_id: int):
    return db.query(Comment).filter(Comment.id == comment_id).first()


def create_comment(db: Session, user_id: int, post_id: int, content: str, score: int = 5):
    comment = Comment(
        user_id=user_id,
        post_id=post_id,
        content=content,
        score=score,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment: Comment):
    db.delete(comment)
    db.commit()
    return comment
