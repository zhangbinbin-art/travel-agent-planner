from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # guest/user/admin
    email = Column(String(100), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Spot(Base):
    __tablename__ = "spots"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(50))
    tags = Column(String(255))
    description = Column(Text)
    score = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(150), nullable=False)
    content = Column(Text)
    heat = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    author = relationship("User")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    spot_id = Column(Integer, ForeignKey("spots.id"), nullable=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    content = Column(Text)
    sentiment = Column(String(20))  # positive/neutral/negative
    score = Column(Integer, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    spot_id = Column(Integer, ForeignKey("spots.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(150))
    plan_data = Column(Text)  # JSON string
    days = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    author = relationship("User")
