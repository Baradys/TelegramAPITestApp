import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.config.config import get_settings
from app.db.database import get_db
from app.db.user.requests import get_app_user, create_user
from app.middleware.jwt import create_tokens, set_auth_cookies
from app.models.request_model import RegisterRequest, LoginRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class AuthRouter:
    def __init__(self, router: APIRouter):
        self.router = router
        self._register_routes()

    def _register_routes(self):
        self.router.post("/auth/register")(self.register)
        self.router.post("/auth/login")(self.login)

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

            tokens = create_tokens(user.id)

            logger.info(f"User {payload.email} registered")

            response = JSONResponse(
                content={"detail": "registered"},
                status_code=201,
            )
            set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
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
            tokens = create_tokens(user.id)

            logger.info(f"User {payload.email} logged in")

            response = JSONResponse(
                content={"detail": "logged in"},
                status_code=201,
            )
            set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
            return response

        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(status_code=401, detail=str(e))
