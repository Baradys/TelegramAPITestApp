from fastapi import APIRouter, Depends

from app.db.user.models import User
from app.middleware.jwt import get_current_user


class UtilsRouter:
    def __init__(self, router: APIRouter):
        self.router = router
        self._register_routes()

    def _register_routes(self):
        self.router.get("/health")(self.health)
        self.router.get("/me")(self.get_me)

    @staticmethod
    async def health():
        """Проверка здоровья"""
        return {"status": "ok"}

    @staticmethod
    async def get_me(user: User = Depends(get_current_user)):
        """Получить информацию о текущем пользователе"""
        return {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        }
