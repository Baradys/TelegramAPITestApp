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
    MessagesRequest, SendMessageRequest, DialogsRequest, PasswordRequest, UserResponse
from app.services.auth import start_auth, verify_code, get_user_profiles, verify_password
from app.services.messages import get_unread_messages, send_message, get_dialogs

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_redis():
    """Dependency для получения Redis клиента"""
    return get_redis_client()


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


@router.post("/profiles/start")
async def start_auth_profile(
        request: PhoneRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Начать авторизацию нового профиля"""

    result = await start_auth(db, user.id, request.phone)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/profiles")
async def list_profiles(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Получить все профили пользователя"""
    result = await get_user_profiles(db, user.id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/profiles/code")
async def auth_verify_code(
        request: CodeRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Подтвердить код"""
    result = await verify_code(db, user.id, request.profile_id, request.code)

    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])

    return result



@router.post("/auth/password", response_model=TokenResponse)
async def auth_verify_password(
        request: PasswordRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Подтвердить пароль 2FA"""
    result = await verify_password(db, user.id, request.profile_id, request.password)

    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])

    user_id = result["user_id"]
    token = create_access_token(user_id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/messages/unread")
async def get_messages_endpoint(
        request: MessagesRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await get_unread_messages(db, user.id, request.profile_id, request.limit)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/messages/send")
async def send_message_endpoint(
        request: SendMessageRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Отправить сообщение от профиля"""
    result = await send_message(db, user.id, request.profile_id, request.text, request.tg_receiver)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/messages/dialogs")
async def get_dialogs_endpoint(
        request: DialogsRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Получить список диалогов профиля"""
    result = await get_dialogs(user.id, request.profile_id, db, request.limit)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/health")
async def health():
    """Проверка здоровья"""
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
    }
