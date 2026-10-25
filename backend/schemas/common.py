from pydantic import BaseModel
from typing import Optional


class UserBrief(BaseModel):
    id: int
    username: str
    role: Optional[str] = None

    class Config:
        from_attributes = True
