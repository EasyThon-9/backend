import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    
    # Database 설정
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    
    # Redis 설정
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # SQLAlchemy URL 생성
    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 전역 설정 인스턴스
settings = Settings()

