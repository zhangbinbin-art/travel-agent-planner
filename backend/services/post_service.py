import json
from datetime import datetime
from sqlalchemy.orm import Session
from models import Post, Spot, PostLike, Comment, CommentLike, User
from typing import Optional


STATUS_TEXT = {0: "待审核", 1: "已通过", 2: "已驳回"}


def _parse_spot_ids(spot_ids_str: str):
    if not spot_ids_str:
        return []
    try:
        data = json.loads(spot_ids_str)
        if isinstance(data, list):
            return [int(x) for x in data]
        return []
    except Exception:
        return []


def _dump_spot_ids(spot_ids_list):
    if not spot_ids_list:
        return "[]"
    try:
        cleaned = []
        for x in spot_ids_list:
            try:
                cleaned.append(int(x))
            except Exception:
                continue
        return json.dumps(cleaned)
    except Exception:
        return "[]"


def recompute_heat(post: Post):
    post.heat = int((post.like_count or 0) * 2 + (post.view_count or 0) + (post.comment_count or 0) * 2)
    return post.heat


def build_post_out(post: Post, db: Session = None, current_user: User = None) -> dict:
    author = getattr(post, "author", None)
    spot_ids = _parse_spot_ids(getattr(post, "spot_ids", "[]"))
    spots = []
    if db is not None and spot_ids:
        spot_objs = db.query(Spot).filter(Spot.id.in_(spot_ids)).all()
        spot_map = {s.id: s for s in spot_objs}
        for sid in spot_ids:
            s = spot_map.get(sid)
            if s:
                spots.append({"id": s.id, "name": s.name, "city": s.city})
    liked = False
    if db is not None and current_user is not None and getattr(current_user, "id", None):
        liked = db.query(PostLike).filter(PostLike.user_id == current_user.id, PostLike.post_id == post.id).first() is not None
    status = getattr(post, "status", 0) or 0
    return {
        "id": post.id,
        "user_id": post.user_id,
        "title": post.title,
        "content": post.content,
        "cover": getattr(post, "cover", None),
        "spot_ids": spot_ids,
        "spots": spots,
        "view_count": int(getattr(post, "view_count", 0) or 0),
        "like_count": int(getattr(post, "like_count", 0) or 0),
        "comment_count": int(getattr(post, "comment_count", 0) or 0),
        "heat": int(getattr(post, "heat", 0) or 0),
        "status": status,
        "status_text": STATUS_TEXT.get(status, str(status)),
        "liked": bool(liked),
        "created_at": getattr(post, "created_at", None),
        "updated_at": getattr(post, "updated_at", None),
        "author": (
            {"id": author.id, "username": author.username, "role": author.role}
            if author
            else None
        ),
    }


def get_posts(
    db: Session,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    sort: str = "latest",
    status: Optional[int] = None,
    spot_id: Optional[int] = None,
    current_user: Optional[User] = None,
):
    query = db.query(Post)
    if status is not None:
        query = query.filter(Post.status == status)
    if keyword:
        keyword = keyword.strip()
        if keyword:
            query = query.filter(Post.title.contains(keyword))
    if spot_id is not None:
        posts_all = query.all()
        filtered = []
        for p in posts_all:
            sids = _parse_spot_ids(getattr(p, "spot_ids", "[]"))
            if spot_id in sids:
                filtered.append(p)
        total = len(filtered)
        if sort == "hot":
            filtered_sorted = sorted(filtered, key=lambda x: (int(x.heat or 0), int(x.id)), reverse=True)
        else:
            filtered_sorted = sorted(filtered, key=lambda x: (x.created_at, int(x.id)), reverse=True)
        start = (page - 1) * page_size
        end = start + page_size
        items = filtered_sorted[start:end]
        return {
            "items": [build_post_out(p, db=db, current_user=current_user) for p in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    if sort == "hot":
        query = query.order_by(Post.heat.desc(), Post.id.desc())
    else:
        query = query.order_by(Post.created_at.desc(), Post.id.desc())
    total = query.count()
    posts = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [build_post_out(p, db=db, current_user=current_user) for p in posts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_post_by_id(db: Session, post_id: int):
    return db.query(Post).filter(Post.id == post_id).first()


def create_post(db: Session, user_id: int, data: dict):
    post_data = dict(data)
    if "spot_ids" in post_data and post_data["spot_ids"] is not None:
        post_data["spot_ids"] = _dump_spot_ids(post_data["spot_ids"])
    else:
        post_data["spot_ids"] = "[]"
    post_data["status"] = 0
    post_data["view_count"] = 0
    post_data["like_count"] = 0
    post_data["comment_count"] = 0
    post_data["heat"] = 0
    post = Post(user_id=user_id, **post_data)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, post: Post, data: dict, is_admin: bool = False):
    post_data = dict(data)
    if "spot_ids" in post_data:
        if post_data["spot_ids"] is None:
            post_data.pop("spot_ids")
        else:
            post_data["spot_ids"] = _dump_spot_ids(post_data["spot_ids"])
    for key, value in post_data.items():
        setattr(post, key, value)
    if not is_admin:
        post.status = 0
    post.updated_at = datetime.utcnow()
    recompute_heat(post)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: Post):
    db.query(CommentLike).filter(CommentLike.comment_id.in_(db.query(Comment.id).filter(Comment.post_id == post.id))).delete(synchronize_session=False)
    db.query(Comment).filter(Comment.post_id == post.id).delete(synchronize_session=False)
    db.query(PostLike).filter(PostLike.post_id == post.id).delete(synchronize_session=False)
    db.delete(post)
    db.commit()
    return post


def toggle_like_post(db: Session, user_id: int, post: Post):
    existing = db.query(PostLike).filter(PostLike.user_id == user_id, PostLike.post_id == post.id).first()
    if existing:
        db.delete(existing)
        post.like_count = max(0, int(post.like_count or 0) - 1)
        liked = False
    else:
        like = PostLike(user_id=user_id, post_id=post.id)
        db.add(like)
        post.like_count = int(post.like_count or 0) + 1
        liked = True
    recompute_heat(post)
    db.commit()
    db.refresh(post)
    return {"liked": liked, "like_count": int(post.like_count or 0)}

