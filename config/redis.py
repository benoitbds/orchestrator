from redis.asyncio import Redis
from langgraph.checkpoint.redis import AsyncRedisSaver
import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def get_redis_client() -> Redis:
    """Get async Redis client with connection pooling."""
    try:
        client = await Redis.from_url(
            REDIS_URL,
            max_connections=50,
            decode_responses=False  # Important pour checkpointing binaire
        )
        # Test connection
        await client.ping()
        logger.info(f"Redis client connected to {REDIS_URL}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis at {REDIS_URL}: {e}")
        raise

async def get_checkpointer() -> AsyncRedisSaver:
    """Get LangGraph checkpointer avec Redis backend."""
    redis_client = await get_redis_client()
    checkpointer = AsyncRedisSaver(redis_client)
    logger.info("LangGraph Redis checkpointer initialized")
    return checkpointer