from celery import Celery
from app.core.config import settings

# 1. Celery 인스턴스 생성
celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 2. 설정 적용
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    enable_utc=True,
)

# 3. Task 자동 검색
celery_app.autodiscover_tasks(['app.domain.LLM'])