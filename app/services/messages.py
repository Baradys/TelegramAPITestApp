# from telethon import TelegramClient
# from sqlalchemy.orm import Session
# # from app.models import Session as SessionModel, MessageCache
# # from app.config import get_settings
# # from cache import cache
# from pathlib import Path
# from datetime import datetime, timedelta
# import json
# import logging
#
# # settings = get_settings()
# logger = logging.getLogger(__name__)
#
# SESSIONS_DIR = "sessions"
#
#
# async def get_unread_messages(user_id: int, db: Session, limit: int = 50):
#     """Получить непрочитанные сообщения"""
#     try:
#         # Получить сессию пользователя
#         # session = db.query(SessionModel).filter(
#         #     SessionModel.user_id == user_id,
#         #     SessionModel.is_active == True
#         # ).first()
#         #
#         # if not session:
#         #     return {"status": "error", "message": "Сессия не найдена"}
#         #
#         ## Проверить кэш
#         # cache_key = f"messages:{user_id}"
#         # cached = await cache.get(cache_key)
#         # if cached:
#         #     logger.info(f"Messages for user {user_id} from cache")
#         #     return cached
#
#         phone = session.phone
#         # session_file = session.session_file
#
#         if not Path(session_file + ".session").exists():
#             return {"status": "error", "message": "Файл сессии не найден"}
#
#         client = TelegramClient(session_file, settings.API_ID, settings.API_HASH)
#
#         try:
#             await client.connect()
#
#             if not await client.is_user_authorized():
#                 session.is_active = False
#                 db.commit()
#                 return {"status": "error", "message": "Сессия истекла"}
#
#             unread_messages = []
#
#             # Получить диалоги
#             dialogs = await client.get_dialogs()
#
#             for dialog in dialogs:
#                 if dialog.unread_count > 0:
#                     entity = dialog.entity
#                     messages = await client.get_messages(
#                         entity,
#                         limit=min(dialog.unread_count, limit)
#                     )
#
#                     for msg in messages:
#                         unread_messages.append({
#                             "id": msg.id,
#                             "from": msg.sender.first_name if msg.sender else "Unknown",
#                             "text": msg.text or "[Медиа]",
#                             "date": msg.date.isoformat(),
#                             "chat_name": dialog.name,
#                             "chat_id": entity.id
#                         })
#
#             # Отметить как прочитанные
#             for dialog in dialogs:
#                 if dialog.unread_count > 0:
#                     await client.send_read_acknowledge(dialog.entity)
#
#             # Обновить last_used
#             session.last_used = datetime.utcnow()
#             db.commit()
#
#             result = {
#                 "status": "success",
#                 "count": len(unread_messages),
#                 "messages": unread_messages
#             }
#
#             # Сохранить в кэш
#             await cache.set(cache_key, result, settings.MESSAGE_CACHE_TTL)
#
#             logger.info(f"Got {len(unread_messages)} messages for user {user_id}")
#
#             return result
#
#         finally:
#             await client.disconnect()
#
#     except Exception as e:
#         logger.error(f"Error getting messages for user {user_id}: {e}")
#         return {"status": "error", "message": str(e)}
#
#
# async def send_message(user_id: int, chat_id: int, text: str, db: Session):
#     """Отправить сообщение"""
#     try:
#         session = db.query(SessionModel).filter(
#             SessionModel.user_id == user_id,
#             SessionModel.is_active == True
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
#                 db.commit()
#                 return {"status": "error", "message": "Сессия истекла"}
#
#             await client.send_message(chat_id, text)
#
#             # Очистить кэш
#             await cache.delete(f"messages:{user_id}")
#
#             logger.info(f"Message sent by user {user_id} to chat {chat_id}")
#
#             return {"status": "success", "message": "Сообщение отправлено"}
#
#         finally:
#             await client.disconnect()
#
#     except Exception as e:
#         logger.error(f"Error sending message for user {user_id}: {e}")
#         return {"status": "error", "message": str(e)}