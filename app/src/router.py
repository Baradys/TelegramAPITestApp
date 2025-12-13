import random
import hashlib
import logging
from datetime import datetime



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.redis import get_redis_client
from app.db.telegram.models import User
from app.middleware.jwt import create_access_token
from app.models.base_model import PhoneRequest, TokenResponse, CodeRequest, RegisterRequest, LoginRequest
from app.services.auth import start_auth, verify_code

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_redis():
    """Dependency для получения Redis клиента"""
    return get_redis_client()

@router.post("/auth/start")
async def auth_start(request: PhoneRequest, db: Session = Depends(get_db)):
    result = await start_auth(123, request.phone, db)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/auth/code", response_model=TokenResponse)
async def auth_verify_code(
        request: CodeRequest,
):
    """Подтвердить код"""
    result = await verify_code(request.phone, request.code)

    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])

    user_id = result["user_id"]
    # token = create_access_token(user_id)

    return {
        # "access_token": token,
        "token_type": "bearer"
    }

#
# @router.post("/auth/password", response_model=TokenResponse)
# async def auth_verify_password(
#         request: PasswordRequest,
#         db: Session = Depends(get_db)
# ):
#     """Подтвердить пароль 2FA"""
#     result = await verify_password(request.phone, request.password, db)
#
#     if result["status"] != "success":
#         raise HTTPException(status_code=400, detail=result["message"])
#
#     user_id = result["user_id"]
#     token = create_access_token(user_id)
#
#     return {
#         "access_token": token,
#         "token_type": "bearer"
#     }


@router.post("/auth/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    try:
        # Проверить, существует ли пользователь

        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Создать пользователя
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        user = User(
            email=request.email,
            password_hash=password_hash
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(user.id)

        logger.info(f"User {request.email} registered")

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Вход пользователя"""
    try:
        user = db.select(User).filter(User.email == request.email).first()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        if user.password_hash != password_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user.last_login = datetime.now()
        db.commit()

        token = create_access_token(user.id)

        logger.info(f"User {request.email} logged in")

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail=str(e))

# ============ УПРАВЛЕНИЕ ПРОФИЛЯМИ ============