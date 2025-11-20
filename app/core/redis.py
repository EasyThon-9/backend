import redis.asyncio as redis
from app.core.config import settings

# 비동기 Redis 커넥션 풀 (애플리케이션 시작 시 한 번만 생성)
_async_redis_pool: redis.ConnectionPool = None

def get_async_redis_pool() -> redis.ConnectionPool:
    """비동기 Redis 커넥션 풀을 반환 (싱글톤 패턴)"""
    global _async_redis_pool
    if _async_redis_pool is None:
        _async_redis_pool = redis.ConnectionPool.from_url(
            settings.CELERY_RESULT_BACKEND,
            encoding="utf-8",
            decode_responses=True
        )
    return _async_redis_pool

# 비동기 Redis (FastAPI용)
async def get_redis_pool():
    pool = get_async_redis_pool()
    return redis.Redis(connection_pool=pool)

# 동기 Redis 커넥션 풀 (Celery용)
import redis as sync_redis

_sync_redis_pool: sync_redis.ConnectionPool = None

def get_sync_redis_pool() -> sync_redis.ConnectionPool:
    """동기 Redis 커넥션 풀을 반환 (싱글톤 패턴)"""
    global _sync_redis_pool
    if _sync_redis_pool is None:
        _sync_redis_pool = sync_redis.ConnectionPool.from_url(
            settings.CELERY_RESULT_BACKEND,
            encoding="utf-8",
            decode_responses=True
        )
    return _sync_redis_pool

def get_sync_redis():
    """동기 Redis 클라이언트 반환"""
    pool = get_sync_redis_pool()
    return sync_redis.Redis(connection_pool=pool)