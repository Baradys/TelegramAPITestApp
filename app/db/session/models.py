from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from datetime import datetime
from app.db.base import Base


class TelegramSession(Base):
    """Сессия для каждого профиля"""
    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("telegram_profiles.id"), index=True)
    session_string = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_used = Column(DateTime, default=datetime.now)