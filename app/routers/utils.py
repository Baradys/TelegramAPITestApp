from fastapi import APIRouter, Depends, Response

from app.db.user.models import User
from app.middleware.jwt import get_current_user, verify_refresh_token, create_tokens, set_auth_cookies, \
    clear_auth_cookies

class UtilsRouter:
    def __init__(self, router: APIRouter):
        self.router = router
        self._register_routes()

    def _register_routes(self):
        self.router.post("/refresh")(self.refresh_tokens)
        self.router.post("/logout")(self.logout)
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

    @staticmethod
    async def refresh_tokens(
            response: Response,
            user: User = Depends(verify_refresh_token)
    ):
        """Обновить access токен используя refresh токен"""
        tokens = create_tokens(user.id)
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])

        return tokens

    @staticmethod
    async def logout(response: Response):
        """Выход пользователя"""
        clear_auth_cookies(response)
        return {"message": "Successfully logged out"}
