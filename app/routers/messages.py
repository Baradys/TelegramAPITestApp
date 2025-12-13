import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.user.models import User
from app.middleware.jwt import get_current_user
from app.models.request_model import SendMessageRequest, DialogsRequest, MessagesRequest
from app.services.messages import get_unread_messages, send_message, get_dialogs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessagesRouter:
    def __init__(self, router: APIRouter):
        self.router = router
        self._register_routes()

    def _register_routes(self):
        self.router.post("/messages/unread")(self.get_messages_endpoint)
        self.router.post("/messages/send")(self.send_message_endpoint)
        self.router.post("/messages/dialogs")(self.get_dialogs_endpoint)

    @staticmethod
    async def get_messages_endpoint(
            request: MessagesRequest,
            user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
    ):
        result = await get_unread_messages(db, user.id, request.profile_id, request.limit)

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])

        return result

    @staticmethod
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

    @staticmethod
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
