from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.domain.LLM import router as llm_router
from app.domain.user import router as user_router
from app.core.database import engine, Base


def create_app() -> FastAPI:
    """
    FastAPI 애플리케이션 팩토리 함수
    앱의 설정, 미들웨어, 라우터 등을 한 곳에서 관리합니다.
    """
    
    # DB 테이블 생성
    Base.metadata.create_all(bind=engine)

    # 앱 초기화
    app = FastAPI(
        title="My Chat Application",
        description="API for Chat Service",
        version="1.0.0"
    )

    api_router = APIRouter(
        prefix="/api"
    )
    api_router.include_router(llm_router, prefix="/llm", tags=["llm"])
    api_router.include_router(user_router, prefix="/user", tags=["user"])
    app.include_router(api_router)
    return app