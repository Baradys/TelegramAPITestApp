import logging
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient

from app.config.config import get_settings
from app.db.telegram.models import User, TelegramProfile, TelegramSession
from app.db.telegram.requests import get_user_by_id, get_profile_by_phone, get_profile_by_user_and_phone, \
    create_profile, update_profile, get_tg_profile, create_tg_session

SESSIONS_DIR = "app/sessions"

Path(SESSIONS_DIR).mkdir(exist_ok=True)

settings = get_settings()

logger = logging.getLogger(__name__)


async def get_client(phone: str):
    """Получить клиент Telethon"""
    session_file = f"{SESSIONS_DIR}/{phone}"
    client = TelegramClient(session_file, settings.API_ID, settings.API_HASH)
    return client


async def start_auth(user_id: int, phone: str, db: AsyncSession):
    """Начать процесс авторизации для профиля"""
    try:
        # Проверить, что пользователь существует
        user = await get_user_by_id(db, user_id)
        if not user:
            return {"status": "error", "message": "Пользователь не найден"}

        # Проверить, есть ли уже такой профиль у другого пользователя
        existing_profile = await get_profile_by_phone(db, phone)
        if existing_profile and existing_profile.user_id != user_id:
            return {
                "status": "error",
                "message": "Этот номер уже используется другим пользователем",
            }

        # Получить профиль текущего пользователя по этому номеру
        profile = await get_profile_by_user_and_phone(db, user_id, phone)

        if profile and profile.is_authorized:
            return {
                "status": "already_authorized",
                "message": "Этот профиль уже авторизован",
                "profile_id": profile.id,
            }

        client = await get_client(phone)

        if not client.is_connected():
            await client.connect()

        # Если уже авторизован в Telethon
        if await client.is_user_authorized():
            if not profile:
                profile = await create_profile(
                    db,
                    user_id=user_id,
                    phone=phone,
                    is_authorized=True,
                )
            else:
                profile = await update_profile(
                    db,
                    profile,
                    is_authorized=True,
                )

            return {
                "status": "already_authorized",
                "message": "Профиль уже авторизован в Telegram",
                "profile_id": profile.id,
            }

        # Отправить код
        result = await client.send_code_request(phone)

        # Сохранить в БД
        if not profile:
            profile = await create_profile(
                db,
                user_id=user_id,
                phone=phone,
                is_authorized=False,
                phone_code_hash=result.phone_code_hash,
            )
        else:
            profile = await update_profile(
                db,
                profile,
                phone_code_hash=result.phone_code_hash,
            )

        logger.info(f"Auth started for user {user_id}, phone {phone}")

        return {
            "status": "code_sent",
            "message": "Код отправлен в Telegram",
            "phone": phone,
            "profile_id": profile.id,
        }

    except Exception as e:
        logger.error(f"Auth start error for user {user_id}, phone {phone}: {e}")
        return {"status": "error", "message": str(e)}


async def verify_code(user_id: int, profile_id: int, code: str, db: AsyncSession):
    """Подтвердить код"""
    try:
        # Получить профиль
        profile = await get_tg_profile(db, user_id, profile_id)

        if not profile:
            return {"status": "error", "message": "Профиль не найден"}

        if not profile.phone_code_hash:
            return {
                "status": "error",
                "message": "Сначала запроси код через /auth/start"
            }

        phone = profile.phone
        client = await get_client(phone)

        if not client.is_connected():
            await client.connect()

        # Используй сохраненный хеш
        try:
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=profile.phone_code_hash
            )
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            raise

        # Получить информацию о профиле
        me = await client.get_me()

        await update_profile(db, profile, is_authorized=True, phone_code_hash=None, first_name=me.first_name,
                             last_name=me.last_name, username=me.username)

        await create_tg_session(db, profile_id, f"{SESSIONS_DIR}/{phone}")

        logger.info(f"User {user_id} authorized profile {profile_id}")

        return {
            "status": "success",
            "message": "Авторизация успешна",
            "profile_id": profile.id,
            "phone": phone,
            "username": me.username
        }

    except Exception as e:
        logger.error(f"Code verification error: {e}")
        return {"status": "error", "message": str(e)}

# async def verify_password(user_id: int, profile_id: int, password: str, db: AsyncSession):
#     """Подтвердить пароль 2FA"""
#     try:
#         profile = db.query(TelegramProfile).filter(
#             TelegramProfile.id == profile_id,
#             TelegramProfile.user_id == user_id
#         ).first()
#
#         if not profile:
#             return {"status": "error", "message": "Профиль не найден"}
#
#         phone = profile.phone
#         client = await get_client(phone)
#
#         if not client.is_connected():
#             await client.connect()
#
#         await client.sign_in(password=password)
#
#         # Получить информацию о профиле
#         me = await client.get_me()
#
#         # Обновить профиль
#         profile.is_authorized = True
#         profile.last_login = datetime.now()
#         profile.phone_code_hash = None
#         profile.first_name = me.first_name
#         profile.last_name = me.last_name
#         profile.username = me.username
#         db.commit()
#
#         # Создать сессию
#         session = TelegramSession(
#             profile_id=profile.id,
#             session_file=f"{SESSIONS_DIR}/{phone}",
#             is_active=True
#         )
#         db.add(session)
#         db.commit()
#
#         logger.info(f"User {user_id} authorized profile {profile_id} with password")
#
#         return {
#             "status": "success",
#             "message": "Авторизация успешна",
#             "profile_id": profile.id
#         }
#
#     except Exception as e:
#         logger.error(f"Password verification error: {e}")
#         return {"status": "error", "message": str(e)}


# async def get_user_profiles(user_id: int, db: AsyncSession):
#     """Получить все профили пользователя"""
#     try:
#         profiles = db.query(TelegramProfile).filter(
#             TelegramProfile.user_id == user_id
#         ).all()
#
#         return {
#             "status": "success",
#             "profiles": [
#                 {
#                     "id": p.id,
#                     "phone": p.phone,
#                     "is_authorized": p.is_authorized,
#                     "is_active": p.is_active,
#                     "first_name": p.first_name,
#                     "last_name": p.last_name,
#                     "username": p.username,
#                     "created_at": p.created_at.isoformat(),
#                     "last_login": p.last_login.isoformat() if p.last_login else None
#                 }
#                 for p in profiles
#             ]
#         }
#
#     except Exception as e:
#         logger.error(f"Error getting profiles for user {user_id}: {e}")
#         return {"status": "error", "message": str(e)}
