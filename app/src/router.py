import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.redis import get_redis_client
from app.db.telegram.models import User
from app.db.telegram.requests import get_app_user, create_user
from app.middleware.jwt import create_access_token, get_current_user
from app.models.base_model import PhoneRequest, TokenResponse, CodeRequest, RegisterRequest, LoginRequest, \
    MessagesRequest
from app.services.auth import start_auth, verify_code
from app.services.messages import get_unread_messages

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_redis():
    """Dependency для получения Redis клиента"""
    return get_redis_client()


@router.post("/profiles/start")
async def start_auth_profile(
        request: PhoneRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Начать авторизацию нового профиля"""

    result = await start_auth(user.id, request.phone, db)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/profiles/code", response_model=TokenResponse)
async def auth_verify_code(
        request: CodeRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Подтвердить код"""
    result = await verify_code(user.id, request.profile_id, request.code, db)

    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])

    return {
        "access_token": create_access_token(user.id),
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
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        existing_user = await get_app_user(db, request.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        user = await create_user(db, request.email, password_hash)

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
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await get_app_user(db, request.email)
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        if not user or user.password_hash != password_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token(user.id)

        logger.info(f"User {request.email} logged in")

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/messages/unread")
async def get_messages_endpoint(
        request: MessagesRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    result = await get_unread_messages(user.id, request.profile_id, db, request.limit)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result
