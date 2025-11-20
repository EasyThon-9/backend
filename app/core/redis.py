import redis.asyncio as redis
from app.core.config import settings

# 비동기 Redis (FastAPI용)
async def get_redis_pool():
    pool = redis.ConnectionPool.from_url(
        settings.CELERY_RESULT_BACKEND, # Redis 주소 재사용
        encoding="utf-8", 
        decode_responses=True
    )
    return redis.Redis(connection_pool=pool)

# 동기 Redis (Celery용)
import redis as sync_redis
def get_sync_redis():
    return sync_redis.from_url(
        settings.CELERY_RESULT_BACKEND,
        encoding="utf-8", 
        decode_responses=True
    )