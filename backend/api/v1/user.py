from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.hash import get_password_hash, verify_password
from core.security import create_access_token
from models import User
from schemas.user import UserRegister, UserLogin, UserOut, Token
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
    user = User(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        email=user_in.email,
        role="user"
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
    return {"access_token": token, "token_type": "bearer"}
