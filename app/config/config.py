from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Telegram
    API_ID: int
    API_HASH: str

    # Database
    DATABASE_URL: str
    DATABASE_PORT: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    # API
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECURE_COOKIES: bool = True
    DEBUG: bool = False

    class Config:
        env_file = "example.env"


@lru_cache()
def get_settings():
    return Settings()
