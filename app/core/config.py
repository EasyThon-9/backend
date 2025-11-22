import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database 설정
    MYSQL_USER: str = "appuser"
    MYSQL_PASSWORD: str = "apppassword"
    MYSQL_DATABASE: str = "easython"
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    
    # Redis 설정
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672/")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
    
    # LLM 설정
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "your-llm-api-key-here")
    
    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    REFRESH_SECRET_KEY: str = os.getenv("REFRESH_SECRET_KEY", "your-refresh-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    
    # SQLAlchemy URL 생성
    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 정의되지 않은 환경 변수 무시

# 전역 설정 인스턴스
settings = Settings()

