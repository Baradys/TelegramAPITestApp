from contextlib import asynccontextmanager
from redis import asyncio as aioredis
from app.config.config import get_settings

settings = get_settings()



REDIS_URL = settings.REDIS_URL

redis_client = None


async def init_redis():
    """Инициализация соединения с Redis"""
    global redis_client
    redis_client = aioredis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()
    print("✅ Redis connected successfully")


async def close_redis():
    """Закрытие соединения с Redis"""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
        print("✅ Redis connection closed")


def get_redis_client():
    """Получение клиента Redis"""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client


@asynccontextmanager
async def redis_lifespan():
    """Context manager для управления жизненным циклом Redis"""
    await init_redis()
    yield
    await close_redis()