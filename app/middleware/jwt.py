from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPBasicCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

import logging

from app.config.config import get_settings
from app.db.database import get_db
from app.db.telegram.models import User

settings = get_settings()
logger = logging.getLogger(__name__)
security = HTTPBearer()


def create_access_token(user_id: int):
    """Создать JWT токен"""
    expire = datetime.now() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"user_id": user_id, "exp": expire}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
        credentials: HTTPBasicCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """Получить текущего пользователя из токена"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
