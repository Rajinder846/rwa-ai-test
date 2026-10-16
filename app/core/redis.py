from functools import lru_cache

import redis.asyncio as redis

from app.config.settings import settings
from app.core.logger import get_logger


logger = get_logger("redis")


@lru_cache
def get_redis_client() -> redis.Redis:
    """
    Return the shared asynchronous Redis client.
    """

    logger.info(
        "initializing_redis",
    )

    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )

async def close_redis_client() -> None:
    """
    Close the shared Redis connection pool.
    """

    redis_client = get_redis_client()

    await redis_client.aclose()

    get_redis_client.cache_clear()

    logger.info(
        "redis_connection_closed",
    )