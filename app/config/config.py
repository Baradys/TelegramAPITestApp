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

    # Redis
    REDIS_URL: str

    # API
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Limits
    # MAX_SESSIONS_PER_USER: int = 3
    # MESSAGE_CACHE_TTL: int = 300  # 5 минут

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
