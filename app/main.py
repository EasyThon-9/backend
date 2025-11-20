from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base

from app.domain.user import model as user_model
from app.domain.chatroom import model as chatroom_model
from app.domain.character import model as character_model
from app.domain.episode import model as episode_model


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



    # 기본 헬스 체크 API
    @app.get("/")
    def read_root():
        return {"status": "ok", "message": "Server is running successfully!"}

    return app

# 앱 객체 생성
app = create_app()

# 직접 실행 시 (python app/main.py)
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )