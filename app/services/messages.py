from sqlalchemy.ext.asyncio import AsyncSession

from app.db.telegram.requests import get_tg_profile, get_tg_session, update_session, update_profile
from app.config.config import get_settings
import logging

from app.services.auth import get_client

settings = get_settings()
logger = logging.getLogger(__name__)


async def get_unread_messages(db: AsyncSession, user_id: int, profile_id: int, limit=50):
    """Получить непрочитанные сообщения для профиля"""
    try:
        profile = await get_tg_profile(db, user_id, profile_id)

        if not profile:
            return {"status": "error", "message": "Профиль не найден"}

        if not profile.is_authorized:
            return {"status": "error", "message": "Профиль не авторизован"}

        session = await get_tg_session(db, profile_id)

        if not session:
            return {"status": "error", "message": "Сессия не найдена"}

        client, session_record = await get_client(profile_id, db)

        try:
            await client.connect()

            if not await client.is_user_authorized():
                await update_session(db, session_record, is_active=False)
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
                        # Для каналов и групп - берем из самого сообщения
                        sender_name = dialog.name  # Имя чата/канала

                        # Если это личное сообщение от пользователя
                        if msg.sender_id and msg.sender:
                            if hasattr(msg.sender, 'first_name'):
                                sender_name = msg.sender.first_name
                            elif hasattr(msg.sender, 'username'):
                                sender_name = msg.sender.username

                        unread_messages.append({
                            "id": msg.id,
                            "from": sender_name,
                            "text": msg.text or "[Медиа]",
                            "date": msg.date.isoformat(),
                            "chat_name": dialog.name,
                            "chat_id": entity.id
                        })

            # Отмечаем как прочитанные
            for dialog in dialogs:
                if dialog.unread_count > 0:
                    await client.send_read_acknowledge(dialog.entity)

            session_record.session_string = client.session.save()
            await db.commit()

            return {
                "status": "success",
                "count": len(unread_messages),
                "messages": unread_messages
            }

        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return {"status": "error", "message": str(e)}



async def get_entity_safe(client, identifier):
    if identifier.isdigit():
        identifier = int(identifier)
    try:
        return await client.get_entity(identifier)
    except ValueError:
        async for dialog in client.iter_dialogs():
            if dialog.id == identifier:
                return dialog.entity
        raise ValueError(f"Entity {identifier} not found")



async def send_message(db: AsyncSession, user_id: int, profile_id: int, text: str, tg_receiver: str):
    """Отправить сообщение от профиля"""
    try:
        profile = await get_tg_profile(db, user_id, profile_id)

        if not profile:
            return {"status": "error", "message": "Профиль не найден"}

        if not profile.is_authorized:
            return {"status": "error", "message": "Профиль не авторизован"}

        session = await get_tg_session(db, profile_id)

        if not session:
            return {"status": "error", "message": "Сессия не найдена"}

        client, session_record = await get_client(profile_id, db)

        try:
            await client.connect()

            if not await client.is_user_authorized():
                await update_session(db, session_record, is_active=False)
                await update_profile(db, profile, is_authorized=False)
                return {"status": "error", "message": "Сессия истекла"}

            entity = await get_entity_safe(client, tg_receiver)
            await client.send_message(entity, text)

            logger.info(f"Message sent from profile {profile_id} to chat {tg_receiver}")

            return {"status": "success", "message": "Сообщение отправлено"}

        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Error sending message from profile {profile_id}: {e}")
        return {"status": "error", "message": str(e)}

async def get_dialogs(user_id: int, profile_id: int, db: AsyncSession, limit: int = 50):
    """Получить список диалогов"""
    try:
        profile = await get_tg_profile(db, user_id, profile_id)

        if not profile:
            return {"status": "error", "message": "Профиль не найден"}

        if not profile.is_authorized:
            return {"status": "error", "message": "Профиль не авторизован"}

        session = await get_tg_session(db, profile_id)

        if not session:
            return {"status": "error", "message": "Сессия не найдена"}

        client, session_record = await get_client(profile_id, db)

        try:
            await client.connect()

            if not await client.is_user_authorized():
                await update_session(db, session_record, is_active=False)
                await update_profile(db, profile, is_authorized=False)
                await db.commit()
                return {"status": "error", "message": "Сессия истекла"}

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

            return {
                "status": "success",
                "dialogs": dialogs_list
            }

        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Error getting dialogs for profile {profile_id}: {e}")
        return {"status": "error", "message": str(e)}
