from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient

from telethon.sessions import StringSession

from app.db.telegram.requests import get_tg_profile, get_tg_session, update_profile, update_session
from app.db.telegram.models import TelegramProfile, TelegramSession, MessageCache
from app.config.config import get_settings
from pathlib import Path
from datetime import datetime
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

SESSIONS_DIR = "sessions"


async def get_unread_messages(user_id: int, profile_id: int, db: AsyncSession, limit: int = 50):
    try:
        profile = await get_tg_profile(db, user_id, profile_id)
        session = await get_tg_session(db, profile_id)

        if not session.session_string:
            return {"status": "error", "message": "Строка сессии не найдена"}

        # Используем StringSession вместо файловой сессии
        client = TelegramClient(
            StringSession(session.session_string),
            settings.API_ID,
            settings.API_HASH
        )

        try:
            await client.connect()

            if not await client.is_user_authorized():
                await update_profile(db, profile, is_authorized=False)
                return {"status": "error", "message": "Сессия истекла"}

            unread_messages = []
            dialogs = await client.get_dialogs()

            for dialog in dialogs:
                if dialog.unread_count > 0:
                    entity = dialog.entity
                    messages = await client.get_messages(
                        entity,
                        limit=min(dialog.unread_count, limit)
                    )

                    for msg in messages:
                        unread_messages.append({
                            "id": msg.id,
                            "from": msg.sender.first_name if msg.sender else "Unknown",
                            "text": msg.text or "[Медиа]",
                            "date": msg.date.isoformat(),
                            "chat_name": dialog.name,
                            "chat_id": entity.id
                        })

            # Отмечаем как прочитанные
            for dialog in dialogs:
                if dialog.unread_count > 0:
                    await client.send_read_acknowledge(dialog.entity)

            return {
                "status": "success",
                "count": len(unread_messages),
                "messages": unread_messages
            }

        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error", "message": str(e)}


async def send_message(user_id: int, profile_id: int, chat_id: int, text: str, db: AsyncSession):
    """Отправить сообщение от профиля"""
    try:
        profile = db.query(TelegramProfile).filter(
            TelegramProfile.id == profile_id,
            TelegramProfile.user_id == user_id
        ).first()

        if not profile:
            return {"status": "error", "message": "Профиль не найден"}

        if not profile.is_authorized:
            return {"status": "error", "message": "Профиль не авторизован"}

        session = db.query(TelegramSession).filter(
            TelegramSession.profile_id == profile_id,
            TelegramSession.is_active == True
        ).first()

        if not session:
            return {"status": "error", "message": "Сессия не найдена"}

        session_file = session.session_file
        client = TelegramClient(session_file, settings.API_ID, settings.API_HASH)

        try:
            await client.connect()

            if not await client.is_user_authorized():
                session.is_active = False
                profile.is_authorized = False
                db.commit()
                return {"status": "error", "message": "Сессия истекла"}

            await client.send_message(chat_id, text)

            logger.info(f"Message sent from profile {profile_id} to chat {chat_id}")

            return {"status": "success", "message": "Сообщение отправлено"}

        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Error sending message from profile {profile_id}: {e}")
        return {"status": "error", "message": str(e)}

# async def get_dialogs(user_id: int, profile_id: int, db: AsyncSession, limit: int = 50):
#     """Получить список диалогов"""
#     try:
#         profile = db.query(TelegramProfile).filter(
#             TelegramProfile.id == profile_id,
#             TelegramProfile.user_id == user_id
#         ).first()
#
#         if not profile:
#             return {"status": "error", "message": "Профиль не найден"}
#
#         if not profile.is_authorized:
#             return {"status": "error", "message": "Профиль не авторизован"}
#
#         session = db.query(TelegramSession).filter(
#             TelegramSession.profile_id == profile_id,
#             TelegramSession.is_active == True
#         ).first()
#
#         if not session:
#             return {"status": "error", "message": "Сессия не найдена"}
#
#         session_file = session.session_file
#         client = TelegramClient(session_file, settings.API_ID, settings.API_HASH)
#
#         try:
#             await client.connect()
#
#             if not await client.is_user_authorized():
#                 session.is_active = False
#                 profile.is_authorized = False
#                 db.commit()
#                 return {"status": "error", "message": "Сессия истекла"}
#
#             dialogs = await client.get_dialogs(limit=limit)
#
#             dialogs_list = [
#                 {
#                     "id": dialog.entity.id,
#                     "name": dialog.name,
#                     "unread_count": dialog.unread_count,
#                     "is_group": dialog.is_group,
#                     "is_channel": dialog.is_channel
#                 }
#                 for dialog in dialogs
#             ]
#
#             return {
#                 "status": "success",
#                 "dialogs": dialogs_list
#             }
#
#         finally:
#             await client.disconnect()
#
#     except Exception as e:
#         logger.error(f"Error getting dialogs for profile {profile_id}: {e}")
#         return {"status": "error", "message": str(e)}
