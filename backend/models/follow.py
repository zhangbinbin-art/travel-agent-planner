"""用户关注关系表：单向关注，不需要对方同意，也不自动互关。"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from core.database import Base


class Follow(Base):
    """user_id 关注 follow_user_id，同一对用户只允许一条记录。"""

    __tablename__ = "follows"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    follow_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "follow_user_id", name="uq_follow_user_target"),
    )
