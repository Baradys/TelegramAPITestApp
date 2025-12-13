import logging
import os
from pathlib import Path

from sqlalchemy.orm import Session
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from app.config.config import get_settings
from app.db.telegram.models import User

SESSIONS_DIR = "sessions"

Path(SESSIONS_DIR).mkdir(exist_ok=True)

settings = get_settings()

logger = logging.getLogger(__name__)


async def get_client(phone: str):
    """Получить клиент Telethon"""
    session_file = f"{SESSIONS_DIR}/{phone}"
    client = TelegramClient(session_file, settings.API_ID, settings.API_HASH)
    return client


async def start_auth(user_id: int, phone: str, db: Session):
    """Начать процесс авторизации"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "Пользователь не найден"}

        if user and user.is_authorized:
            return {
                "status": "already_authorized",
                "message": "Пользователь уже авторизован"
            }

        client = await get_client(phone)

        if not client.is_connected():
            await client.connect()
        #
        #     # Если уже авторизован в Telethon
        #     if await client.is_user_authorized():
        #         if not user:
        #             user = User(phone=phone, is_authorized=True)
        #             db.add(user)
        #         else:
        #             user.is_authorized = True
        #         db.commit()
        #
        #         return {
        #             "status": "already_authorized",
        #             "message": "Уже авторизован в Telegram"
        #         }
        #
        #     # Отправить код
        result = await client.send_code_request(phone)

        # Сохранить в БД
        if not user:
            user = User(
                phone=phone,
                is_authorized=False,
                phone_code_hash=result.phone_code_hash  # ← СОХРАНИ ХЕШ
            )
            db.add(user)
        else:
            user.phone_code_hash = result.phone_code_hash

        db.commit()

        logger.info(f"Auth started for {phone}")

        return {
            "status": "code_sent",
            "message": result.phone_code_hash
        }

    except Exception as e:
        logger.error(f"Auth start error for {phone}: {e}")
        return {"status": "error", "message": str(e)}


async def verify_code(phone: str, code: str):
    client = await get_client(phone)

    if not client.is_connected():
        await client.connect()

    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        return {"status": "success", "message": "Авторизация успешна"}
    except SessionPasswordNeededError:
        return {
            "status": "password_needed",
            "message": "Требуется пароль двухфакторной аутентификации"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# async def verify_password(phone: str, password: str):
#     """Подтвердить пароль 2FA"""
#     client = await get_or_create_client(phone)
#
#     if not client.is_connected():
#         await client.connect()
#
#     try:
#         await client.sign_in(password=password)
#         return {"status": "success", "message": "Авторизация успешна"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}
