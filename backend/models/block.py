"""拉黑关系（user_blocks）：user_id 拉黑了 blocked_user_id。"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from core.database import Base


class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = (UniqueConstraint("user_id", "blocked_user_id", name="uq_block_pair"),)

    id = Column(Integer, primary_key=True, index=True)
    # 拉黑发起人
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 被拉黑的人
    blocked_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
