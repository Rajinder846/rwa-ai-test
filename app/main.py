from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.config.settings import settings
from app.core.logger import configure_logging
from app.core.redis import (
    close_redis_client,
    get_redis_client,
)
from app.core.exception_handlers import (
    app_exception_handler,
    unexpected_exception_handler,
)
from app.core.exceptions import AppException

@asynccontextmanager
async def lifespan(app: FastAPI):

    # -------------------------
    # Startup
    # -------------------------

    configure_logging()

    redis_client = get_redis_client()

    await redis_client.ping()

    yield

    # -------------------------
    # Shutdown
    # -------------------------

    await close_redis_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_exception_handler(
        AppException,
        app_exception_handler,
    )

    app.add_exception_handler(
        Exception,
        unexpected_exception_handler,
    )

    app.include_router(health_router)
    app.include_router(chat_router)

    return app


app = create_app()