import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db.base import Base
from app.db.database import engine
from app.db.redis import init_redis, close_redis
from app.src.router import router


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    await init_models()  # создаём таблицы асинхронно
    await init_redis()

    yield

    # Shutdown
    await close_redis()


def get_application():
    application = FastAPI(
        title="API Service",
        description="API Service for barrier control",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    application.include_router(router)
    return application


app = get_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
