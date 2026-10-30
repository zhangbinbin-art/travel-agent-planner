from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.hash import get_password_hash, verify_password
from core.security import create_access_token
from api.deps import get_current_user
from models import User
from schemas.user import UserRegister, UserLogin, UserOut, Token, RealNameRequest
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
