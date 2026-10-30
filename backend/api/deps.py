from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError
from core.config import settings
from sqlalchemy.orm import Session
from core.database import get_db
from models import Hotel, User

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


def require_merchant_hotel(
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
) -> int:
    """商家已审核且必须绑定唯一酒店，返回 hotel_id。

    绑定关系完全由后端 token + 数据库决定，忽略前端传入的任何 hotel_id 参数；
    商户侧所有查询都必须使用本函数返回的 hotel_id 做强制隔离。
    """
    hotel_id = getattr(current_user, "merchant_hotel_id", None)
    if not hotel_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="商家账号未绑定酒店，请联系管理员")
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="绑定酒店不存在，请联系管理员")
    if hotel.merchant_id is not None and hotel.merchant_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="酒店绑定关系异常，请联系管理员")
    return hotel_id


def require_any_auth(current_user: User = Depends(get_current_user)):
    role = getattr(current_user, "role", None)
    if role not in ("user", "merchant", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return current_user
