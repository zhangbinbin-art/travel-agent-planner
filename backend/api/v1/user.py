from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.hash import get_password_hash, verify_password
from core.security import create_access_token
from api.deps import get_current_user, get_optional_user
from models import User
from schemas.user import UserRegister, UserLogin, UserOut, Token, RealNameRequest
from schemas.follow import FollowRequest, FollowListResponse, UserPostsResponse
from schemas.message import MessageSendRequest, MessageSchema, ChatResponse
from services import follow_service, message_service, post_service
import re

router = APIRouter()

@router.post("/register", response_model=UserOut)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    if not user_in.username or not str(user_in.username).strip():
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    pwd = user_in.password or ""
    if len(pwd) < 6 or len(pwd) > 12:
        raise HTTPException(status_code=400, detail="密码必须包含字母和数字")
    if not re.search(r'[A-Za-z]', pwd) or not re.search(r'[0-9]', pwd):
        raise HTTPException(status_code=400, detail="密码必须包含字母和数字")
    role = (user_in.role or "user").strip().lower()
    if role not in ("user", "merchant"):
        raise HTTPException(status_code=400, detail="注册角色只能为 user 或 merchant")
    user = User(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        email=user_in.email,
        role=role,
        # 商家注册后默认待审核，管理员审核通过后才能进入商家后台
        audit_status="pending" if role == "merchant" else "approved",
        shop_name=user_in.shop_name if role == "merchant" else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "audit_status": getattr(user, "audit_status", "approved") or "approved",
        "user_id": user.id,
        "username": user.username,
        "is_real_name_auth": bool(getattr(user, "is_real_name_auth", False)),
        "merchant_hotel_id": getattr(user, "merchant_hotel_id", None),
    }


@router.get("/profile", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/real-name", response_model=UserOut)
def submit_real_name(
    payload: RealNameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """模拟实名校验：仅校验格式并落库，不调用公安接口。"""
    id_card = payload.id_card.strip().upper()
    if not re.match(r"^\d{17}[\dX]$", id_card):
        raise HTTPException(status_code=400, detail="身份证号格式不正确")
    current_user.real_name = payload.real_name.strip()
    current_user.id_card = id_card
    current_user.is_real_name_auth = True
    db.commit()
    db.refresh(current_user)
    return current_user


# ---------- 关注 / 粉丝 ----------

@router.post("/follow")
def toggle_follow(
    payload: FollowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关注或取关：已关注则删除关系，未关注则创建。"""
    if payload.follow_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")
    target = db.query(User).filter(User.id == payload.follow_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    return follow_service.toggle_follow(db, current_user.id, payload.follow_user_id)


@router.get("/follow-list", response_model=FollowListResponse)
def list_my_following(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我关注的人。"""
    return follow_service.list_following(db, current_user.id, page=page, page_size=page_size)


@router.get("/fans-list", response_model=FollowListResponse)
def list_my_fans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关注我的人（粉丝）。"""
    return follow_service.list_fans(db, current_user.id, page=page, page_size=page_size)


@router.get("/user-posts/{target_user_id}", response_model=UserPostsResponse)
def list_user_posts(
    target_user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
    viewer: User = Depends(get_optional_user),
):
    """指定用户的游记列表，按 visible 规则过滤（仅作者/管理员可见非公开游记）。"""
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    data = post_service.get_author_posts(
        db, target_user_id, viewer=viewer, page=page, page_size=page_size
    )
    data["user"] = follow_service.build_user_brief(target)
    data["is_following"] = follow_service.is_following(db, getattr(viewer, "id", None), target_user_id)
    data["viewer_is_self"] = bool(viewer is not None and int(viewer.id) == int(target_user_id))
    data["following_count"] = follow_service.count_following(db, target_user_id)
    data["follower_count"] = follow_service.count_fans(db, target_user_id)
    return data


# ---------- 私聊 ----------

@router.post("/message/send", response_model=MessageSchema)
def send_chat_message(
    payload: MessageSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送私聊消息：对方未回复前只能发一条。"""
    if payload.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己发消息")
    target = db.query(User).filter(User.id == payload.receiver_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    try:
        return message_service.send_message(db, current_user.id, payload.receiver_id, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/message/chat/{target_user_id}", response_model=ChatResponse)
def get_chat_history(
    target_user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """与某用户的聊天记录（时间正序），并返回当前是否允许发送。"""
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    data = message_service.get_chat(db, current_user.id, target_user_id, page=page, page_size=page_size)
    data["target_user"] = follow_service.build_user_brief(target)
    return data
