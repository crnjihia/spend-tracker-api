"""Redis connection and dependency management."""

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_redis_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Return active asynchronous Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            str(settings.REDIS_URL),
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


def set_redis(client: Optional[aioredis.Redis]) -> None:
    """Set the Redis client (useful for unit testing with fakeredis)."""
    global _redis_client
    _redis_client = client
