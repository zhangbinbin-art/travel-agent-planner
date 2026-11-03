from pydantic import BaseModel, Field
from typing import Optional

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=50)
    # 用户 / 商家注册必填手机号
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = None
    role: Optional[str] = "user"  # user / merchant
    shop_name: Optional[str] = None

class UserLogin(BaseModel):
    # 账号密码登录（管理员 / 兼容旧账号）
    username: Optional[str] = None
    password: str
    # 手机号登录：phone + role_type（user / shop）
    phone: Optional[str] = None
    role_type: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    audit_status: Optional[str] = "approved"
    shop_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_real_name_auth: Optional[bool] = False
    real_name: Optional[str] = None
    id_card: Optional[str] = None
    merchant_hotel_id: Optional[int] = None

    class Config:
        from_attributes = True


class RealNameRequest(BaseModel):
    real_name: str = Field(min_length=2, max_length=50)
    id_card: str = Field(min_length=15, max_length=30)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # 登录成功后一并返回角色与审核状态，便于前端做跳转与待审核提示
    role: Optional[str] = None
    audit_status: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    is_real_name_auth: Optional[bool] = False
    merchant_hotel_id: Optional[int] = None
