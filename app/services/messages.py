from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import get_settings
import logging

from app.db.profile.requests import get_tg_profile, update_profile
from app.db.session.requests import get_tg_session, update_session
from app.services.auth import _get_client

settings = get_settings()
logger = logging.getLogger(__name__)

async def _get_tg_entity(client, identifier):
    if identifier.isdigit():
        identifier = int(identifier)
    try:
        return await client.get_entity(identifier)
    except ValueError:
        async for dialog in client.iter_dialogs():
            if dialog.id == identifier:
                return dialog.entity
        raise ValueError(f"Entity {identifier} not found")


async def _prepare_authorized_client(
        db,
        user_id: int,
        profile_username: str,
):
    """
    Общая подготовка клиента:
    - проверка профиля
    - проверка авторизации
    - проверка сессии
    - создание и подключение клиента

    Возвращает:
      - error: dict со статусом и сообщением (если ошибка), иначе None
      - client: TelegramClient или None
      - session_record: объект записи сессии или None
    """
    profile = await get_tg_profile(db, user_id, profile_username)
    if not profile:
        return {"status": "error", "message": "Профиль не найден"}, None, None

    if not profile.is_authorized:
        return {"status": "error", "message": "Профиль не авторизован"}, None, None

    session = await get_tg_session(db, profile_username)
    if not session:
        return {"status": "error", "message": "Сессия не найдена"}, None, None

    client, session_record = await _get_client(db, profile_username)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            await update_session(db, session_record, is_active=False)
            await update_profile(db, profile, is_authorized=False)
            return {"status": "error", "message": "Сессия истекла"}, None, None

    except Exception:
        await update_session(db, session_record, is_active=False)
        await update_profile(db, profile, is_authorized=False)
        return {"status": "error", "message": "Ошибка подключения к Telegram"}, None, None

    return None, client, session_record


async def get_unread_messages(
        db: AsyncSession,
        user_id: int,
        profile_username: str,
        limit: int = 50,
):
    """Получить непрочитанные сообщения для профиля"""
    try:
        error, client, session_record = await _prepare_authorized_client(
            db=db,
            user_id=user_id,
            profile_username=profile_username,
        )
        if error:
            return error

        try:
            unread_messages = []
            dialogs = await client.get_dialogs()

            for dialog in dialogs:
                if dialog.unread_count <= 0:
                    continue

                entity = dialog.entity
                messages = await client.get_messages(
                    entity,
                    limit=min(dialog.unread_count, limit),
                )

                for msg in messages:
                    sender_name = dialog.name  # имя чата/канала по умолчанию

                    # Личные сообщения
                    if msg.sender_id and msg.sender:
                        if getattr(msg.sender, "first_name", None):
                            sender_name = msg.sender.first_name
                        elif getattr(msg.sender, "username", None):
                            sender_name = msg.sender.username

                    unread_messages.append(
                        {
                            "id": msg.id,
                            "from": sender_name,
                            "text": msg.text or "[Медиа]",
                            "date": msg.date.isoformat(),
                            "chat_name": dialog.name,
                            "chat_id": entity.id,
                        }
                    )
            # Отмечаем как прочитанные
            for dialog in dialogs:
                if dialog.unread_count > 0:
                    await client.send_read_acknowledge(dialog.entity)

            session_record.session_string = client.session.save()
            await db.commit()
            logger.info(f"User {user_id} got unread messages for profile {profile_username}")
            return {
                "status": "success",
                "count": len(unread_messages),
                "messages": unread_messages,
            }

        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return {"status": "error", "message": str(e)}


async def send_message(db: AsyncSession, user_id: int, profile_username: str, text: str, tg_receiver: str):
    """Отправить сообщение от профиля"""
    try:
        error, client, session_record = await _prepare_authorized_client(
            db=db,
            user_id=user_id,
            profile_username=profile_username,
        )
        if error:
            return error

        try:
            entity = await _get_tg_entity(client, tg_receiver)
            await client.send_message(entity, text)
            logger.info(f"Message sent from profile {profile_username} to chat {tg_receiver}")
            return {"status": "success", "message": "Сообщение отправлено"}

        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Error sending message from profile {profile_username}: {e}")
        return {"status": "error", "message": str(e)}


async def get_dialogs(user_id: int, profile_username: str, db: AsyncSession, limit: int = 50):
    """Получить список диалогов"""
    try:
        error, client, session_record = await _prepare_authorized_client(
            db=db,
            user_id=user_id,
            profile_username=profile_username,
        )
        if error:
            return error
        try:
            dialogs = await client.get_dialogs(limit=limit)

            dialogs_list = [
                {
                    "id": dialog.entity.id,
                    "name": dialog.name,
                    "unread_count": dialog.unread_count,
                    "is_group": dialog.is_group,
                    "is_channel": dialog.is_channel
                }
                for dialog in dialogs
            ]
            logger.info(f"User {user_id} got dialogs for profile {profile_username}")
            return {
                "status": "success",
                "dialogs": dialogs_list
            }

        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Error getting dialogs for profile {profile_username}: {e}")
        return {"status": "error", "message": str(e)}
