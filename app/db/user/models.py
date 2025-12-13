from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base



class User(Base):
    """Основной пользователь системы"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
