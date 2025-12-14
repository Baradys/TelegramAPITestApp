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

    class ConfigDict:
        env_file = "example.env"


    @classmethod
    def for_testing(cls):
        """Создание тестовых настроек"""
        return cls(
            API_ID=123456,
            API_HASH="test_api_hash",
            DATABASE_URL="localhost",
            DATABASE_PORT="5432",
            DATABASE_NAME="test_db",
            DATABASE_USER="test_user",
            DATABASE_PASSWORD="test_pass",
            SECRET_KEY="test_secret_key"
        )


@lru_cache()
def get_settings():
    return Settings()
