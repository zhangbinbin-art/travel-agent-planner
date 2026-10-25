from sqlalchemy.orm import Session
from models import Post
from typing import Optional


def build_post_out(post: Post) -> dict:
    author = post.author
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "heat": post.heat or 0,
        "user_id": post.user_id,
        "created_at": post.created_at,
        "author": (
            {"id": author.id, "username": author.username, "role": author.role}
            if author
            else None
        ),
    }


def get_posts(db: Session, keyword: Optional[str] = None, page: int = 1, page_size: int = 10):
    query = db.query(Post)
    if keyword:
        keyword = keyword.strip()
        if keyword:
            query = query.filter(Post.title.contains(keyword))
    total = query.count()
    posts = (
        query.order_by(Post.created_at.desc(), Post.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [build_post_out(p) for p in posts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_post_by_id(db: Session, post_id: int):
    return db.query(Post).filter(Post.id == post_id).first()


def create_post(db: Session, user_id: int, data: dict):
    post = Post(user_id=user_id, **data)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, post: Post, data: dict):
    for key, value in data.items():
        if value is not None:
            setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: Post):
    db.delete(post)
    db.commit()
    return post
