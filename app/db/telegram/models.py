from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from datetime import datetime
from app.db.base import Base


class User(Base):
    """Основной пользователь системы"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)



class TelegramProfile(Base):
    """Профиль Telegram (номер телефона)"""
    __tablename__ = "telegram_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    phone = Column(String(20), unique=True, index=True)
    phone_code_hash = Column(String(255), nullable=True)
    is_authorized = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)

    # Метаданные профиля
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    profile_photo_id = Column(String(255), nullable=True)


class TelegramSession(Base):
    """Сессия для каждого профиля"""
    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("telegram_profiles.id"), index=True)
    session_file = Column(String(255), unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_used = Column(DateTime, default=datetime.now)


class MessageCache(Base):
    """Кэш сообщений"""
    __tablename__ = "message_cache"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("telegram_profiles.id"), index=True)
    message_data = Column(Text)  # JSON
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)