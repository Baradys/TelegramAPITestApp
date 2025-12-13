import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.user.models import User
from app.middleware.jwt import get_current_user
from app.models.request_model import PhoneRequest, CodeRequest
from app.services.auth import start_auth, verify_code, get_user_profiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProfilesRouter:
    def __init__(self, router: APIRouter):
        self.router = router
        self._register_routes()

    def _register_routes(self):
        self.router.get("/profiles")(self.list_profiles)
        self.router.post("/profiles/start")(self.start_auth_profile)
        self.router.post("/profiles/code")(self.auth_verify_code)

    @staticmethod
    async def list_profiles(
            user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
    ):
        """Получить все профили пользователя"""
        result = await get_user_profiles(db, user.id)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])

        return result

    @staticmethod
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

    @staticmethod
    async def auth_verify_code(
            request: CodeRequest,
            user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
    ):
        """Подтвердить код"""
        result = await verify_code(db, user.id, request.profile_username, request.code)

        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result["message"])

        return result
