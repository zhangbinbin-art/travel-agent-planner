from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError
from core.config import settings
from sqlalchemy.orm import Session
from core.database import get_db
from models import User

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

def require_admin(current_user: User = Depends(get_current_user)):
    if getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return current_user


def require_role(roles: list[str]):
    def _checker(current_user: User = Depends(get_current_user)):
        role = getattr(current_user, "role", None)
        if role not in roles:
            if "admin" in roles:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current_user
    return _checker


def require_merchant(current_user: User = Depends(get_current_user)):
    """商家专属依赖：必须是 role=merchant 且审核通过（approved）。"""
    if getattr(current_user, "role", None) != "merchant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if getattr(current_user, "audit_status", None) != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="商家账号待审核或未通过审核")
    return current_user


def require_merchant_hotel(current_user: User = Depends(require_merchant)) -> int:
    """商家已审核且必须绑定唯一酒店，返回 hotel_id。"""
    hotel_id = getattr(current_user, "merchant_hotel_id", None)
    if not hotel_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="商家账号未绑定酒店，请联系管理员")
    return hotel_id


def require_any_auth(current_user: User = Depends(get_current_user)):
    role = getattr(current_user, "role", None)
    if role not in ("user", "merchant", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return current_user
