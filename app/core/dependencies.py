from fastapi import Depends
from sqlalchemy.orm import Session
import redis.asyncio as redis
from app.core.database import SessionLocal
from app.core.redis import get_redis_pool


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_redis_client() -> redis.Redis:
    """Redis 클라이언트 의존성"""
    redis_client = await get_redis_pool()
    try:
        yield redis_client
    finally:
        await redis_client.aclose()

