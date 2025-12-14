import logging

from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config.config import get_settings
from app.db.profile.requests import get_profile_by_phone, create_profile, update_profile, \
    get_users_profiles, get_tg_profile
from app.db.session.requests import get_tg_session, update_session, create_tg_session
from app.db.user.requests import get_user_by_id

settings = get_settings()

logger = logging.getLogger(__name__)


async def _prepare_client_for_profile(
        db,
        user_id: int,
        phone: str,
        require_phone_code_hash: bool = True,
):
    """
    Возвращает (profile, client, session_record) или словарь-ошибку.

    require_phone_code_hash:
      - True  — проверять наличие profile.phone_code_hash
      - False — не проверять (если где‑то это не нужно)
    """
    profile = await get_tg_profile(db, user_id, phone)

    if not profile:
        return {"status": "error", "message": "Профиль не найден"}

    if require_phone_code_hash and not profile.phone_code_hash:
        return {
            "status": "error",
            "message": "Сначала запроси код через /auth/start",
        }

    client, session_record = await _get_client(db, phone)

    if not client.is_connected():
        await client.connect()

    return profile, client, session_record


async def _get_client(db: AsyncSession, phone: str):
    """Получить клиент Telethon из StringSession"""

    # Получаем сессию из БД
    session_record = await get_tg_session(db, phone)

    # Используем существующую сессию или создаем пустую
    session_string = session_record.session_string if session_record else None
    session = StringSession(session_string)

    client = TelegramClient(session, settings.API_ID, settings.API_HASH)

    return client, session_record


async def start_auth(db: AsyncSession, user_id: int, phone: str):
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
        profile = await get_tg_profile(db, user_id, phone)

        if profile and profile.is_authorized:
            logger.info(f"User {user_id} already authorized profile {phone}")
            return {
                "status": "already_authorized",
                "message": "Этот профиль уже авторизован",
                "phone": phone,
            }

        if not profile:
            profile = await create_profile(
                db,
                user_id=user_id,
                phone=phone,
                is_authorized=False,
            )

        client, session_record = await _get_client(db, phone)

        if not client.is_connected():
            await client.connect()

        # Если уже авторизован в Telethon
        if await client.is_user_authorized():
            await update_profile(
                db,
                profile,
                is_authorized=True,
            )
            logger.info(f"User {user_id} already authorized profile {phone}")
            return {
                "status": "already_authorized",
                "message": "Профиль уже авторизован в Telegram",
                "phone": phone,
            }

        # Отправить код
        result = await client.send_code_request(phone)

        session_string = client.session.save()
        if session_record:
            # Обновить существующую сессию
            await update_session(db, session_record, session_string=session_string)
        else:
            # Создать новую сессию
            await create_tg_session(db, profile.id, session_string)
        await update_profile(
            db,
            profile,
            phone_code_hash=result.phone_code_hash,
        )
        logger.info(f"Auth started for user {user_id}, phone {phone}")
        return {
            "status": "code_sent",
            "message": "Код отправлен в Telegram",
            "phone": phone,
        }

    except Exception as e:
        logger.error(f"Auth start error for user {user_id}, phone {phone}: {e}")
        return {"status": "error", "message": str(e)}


async def verify_code(db: AsyncSession, user_id: int, phone: str, code: str):
    """Подтвердить код"""
    try:
        result = await _prepare_client_for_profile(db, user_id, phone)

        # Если вернулся словарь — это ошибка, сразу отдаём в ответ
        if isinstance(result, dict):
            return result

        profile, client, session_record = result

        if not client.is_connected():
            await client.connect()

        # Используй сохраненный хеш
        try:
            await client.sign_in(
                phone=profile.phone,
                code=code,
                phone_code_hash=profile.phone_code_hash
            )
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            raise
        session_string = client.session.save()
        await update_session(db, session_record, session_string=session_string)
        # Получить информацию о профиле
        me = await client.get_me()

        await update_profile(db, profile, is_authorized=True, phone_code_hash=None, first_name=me.first_name,
                             last_name=me.last_name, username=me.username)

        logger.info(f"User {user_id} authorized profile {phone}")
        return {
            "status": "success",
            "message": "Авторизация успешна",
            "phone": profile.phone,
            "username": me.username
        }

    except Exception as e:
        logger.error(f"Code verification error: {e}")
        return {"status": "error", "message": str(e)}


async def verify_password(db: AsyncSession, user_id: int, phone: str, password: str):
    """Подтвердить пароль 2FA"""
    try:
        result = await _prepare_client_for_profile(db, user_id, phone)

        # Если вернулся словарь — это ошибка, сразу отдаём в ответ
        if isinstance(result, dict):
            return result

        profile, client, session_record = result

        if not client.is_connected():
            await client.connect()

        await client.sign_in(password=password)

        # Получить информацию о профиле
        me = await client.get_me()

        # Обновить профиль
        await update_profile(db, profile, is_authorized=True, phone_code_hash=None, first_name=me.first_name,
                             last_name=me.last_name, username=me.username)

        # Создать сессию

        session_string = client.session.save()
        await update_session(db, session_record, session_string=session_string)

        logger.info(f"User {user_id} authorized profile {phone} with password")

        return {
            "status": "success",
            "message": "Авторизация успешна",
            "phone": phone
        }

    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return {"status": "error", "message": str(e)}


async def get_user_profiles(db: AsyncSession, user_id: int):
    """Получить все профили пользователя"""
    try:
        profiles = await get_users_profiles(db, user_id)
        logger.info(f"User {user_id} got profiles: {profiles}")
        return {
            "status": "success",
            "profiles": [
                {
                    "id": p.id,
                    "phone": p.phone,
                    "is_authorized": p.is_authorized,
                    "is_active": p.is_active,
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "username": p.username,
                    "created_at": p.created_at.isoformat(),
                    "last_login": p.last_login.isoformat() if p.last_login else None
                }
                for p in profiles
            ]
        }

    except Exception as e:
        logger.error(f"Error getting profiles for user {user_id}: {e}")
        return {"status": "error", "message": str(e)}
