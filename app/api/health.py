from fastapi import APIRouter

from app.config.settings import settings
from app.core.logger import get_logger
from app.core.redis import get_redis_client


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

logger = get_logger("health")


@router.get("")
async def health_check():

    print("health check")

    redis_client = get_redis_client()

    redis_status = "healthy"

    try:
        await redis_client.ping()

        await redis_client.set("health", "healthy")

        print("redisss",await redis_client.get("health"))
    except Exception as exc:
        redis_status = "unhealthy"

        logger.error(
            "redis_health_check_failed",
            error=str(exc),
        )

    logger.info(
        "health_check",
        service=settings.app_name,
        version=settings.app_version,
        redis_status=redis_status,
    )

    return {
        "status": "healthy!",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "dependencies": {
            "redis": redis_status,
        },
    }