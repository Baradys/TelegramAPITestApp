from typing import Optional

from fastapi import Depends, HTTPException, status, Cookie, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

import logging

from app.config.config import get_settings
from app.db.database import get_db
from app.db.user.models import User
from app.db.user.requests import get_user_by_id

settings = get_settings()
logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


def create_access_token(user_id: int):
    """Создать JWT токен"""
    expire = datetime.now() + timedelta(
        days=settings.ACCESS_TOKEN_EXPIRE_DAYS
    )
    to_encode = {"user_id": user_id, "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(user_id: int) -> str:
    """Создать JWT refresh токен"""
    expire = datetime.now() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = {"user_id": user_id, "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_tokens(user_id: int) -> dict:
    """Создать пару access и refresh токенов"""
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer"
    }


def clear_auth_cookies(response: Response):
    """Удалить токены из cookies"""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Установить токены в cookies"""
    # Access token - короткоживущий
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    # Refresh token - долгоживущий
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )


async def get_current_user(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        access_token: Optional[str] = Cookie(None),
        db: AsyncSession = Depends(get_db)
) -> User:
    """Получить текущего пользователя по access токену"""

    jwt_token = None
    if credentials:
        jwt_token = credentials.credentials
    elif access_token:
        jwt_token = access_token

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            jwt_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Проверяем тип токена
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.user = user
    return user


async def verify_refresh_token(
        refresh_token: Optional[str] = Cookie(None),
        db: AsyncSession = Depends(get_db)
) -> User:
    """Проверить refresh токен и вернуть пользователя"""

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )

    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Проверяем тип токена
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
