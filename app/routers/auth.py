import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.db.database import get_db
from app.db.user.models import User
from app.db.user.requests import get_app_user, create_user
from app.middleware.jwt import create_access_token, get_current_user
from app.models.request_model import RegisterRequest, LoginRequest, PasswordRequest
from app.services.auth import verify_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthRouter:
    def __init__(self, router: APIRouter):
        self.router = router
        self._register_routes()

    def _register_routes(self):
        self.router.post("/auth/register")(self.register)
        self.router.post("/auth/login")(self.login)
        self.router.post("/auth/password")(self.password)

    @staticmethod
    async def register(
            payload: RegisterRequest,
            db: AsyncSession = Depends(get_db),
    ):
        try:
            existing_user = await get_app_user(db, payload.email)
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
            password_hash = hashlib.sha256(payload.password.encode()).hexdigest()
            user = await create_user(db, payload.email, password_hash)

            token = create_access_token(user.id)

            logger.info(f"User {payload.email} registered")

            response = JSONResponse(
                content={"detail": "registered"},  # можешь вернуть что угодно
                status_code=201,
            )
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=60 * 60 * 24
            )
            return response

        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def login(
            payload: LoginRequest,
            db: AsyncSession = Depends(get_db),
    ):
        try:
            user = await get_app_user(db, payload.email)
            password_hash = hashlib.sha256(payload.password.encode()).hexdigest()
            if not user or user.password_hash != password_hash:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            token = create_access_token(user.id)

            logger.info(f"User {payload.email} logged in")

            response = JSONResponse(
                content={"detail": "logged in"},
                status_code=201,
            )
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=60 * 60 * 24
            )
            return response

        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(status_code=401, detail=str(e))

    @staticmethod
    async def password(
            request: PasswordRequest,
            user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
    ):
        """Подтвердить пароль 2FA"""
        result = await verify_password(db, user.id, request.profile_username, request.password)

        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result["message"])

        return result
