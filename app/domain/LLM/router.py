from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.domain.LLM.schemas import (
    GetLLMMessageRequest, 
    GetLLMMessageResponse,
    GetLLMFeedbackResponse,
    GetLLMResultResponse
)
from app.domain.LLM.task import get_llm_message, get_gpt_feedback, get_gpt_result
from app.core.redis import get_redis_pool
from app.core.database import SessionLocal
from app.core.security import get_current_user_id
from app.domain.user.repository import UserRepository, ChatRoomRepository
import redis.asyncio as redis

router = APIRouter()

def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_redis_client() -> redis.Redis:
    """Redis 클라이언트 의존성 (FastAPI의 의존성 주입 사용)"""
    redis_client = await get_redis_pool()
    try:
        yield redis_client
    finally:
        # 연결을 풀에 반환 (풀링을 사용하므로 연결이 풀에 반환됨)
        await redis_client.aclose()

@router.post("/message", response_model=GetLLMMessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_llm_message(
    request: GetLLMMessageRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    # User 조회하여 email 가져오기
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user_email = user.email
    
    # episode_id 저장
    episode_key = f"episode_id:{user_email}"
    if await redis_client.exists(episode_key):
        await redis_client.delete(episode_key)
    await redis_client.set(episode_key, request.episode_id)
    
    # count 증가 (INCR은 키가 없을 경우 0으로 초기화 후 1 증가)
    count_key = f"count:{user_email}"
    await redis_client.incr(count_key)
        
    # character_id 저장
    char_key = f"character_id:{user_email}"
    await redis_client.set(char_key, request.character_id)

    # 2. Celery Task 실행
    task = get_llm_message.delay(
        character_id=request.character_id, 
        episode_id=request.episode_id, 
        user_email=user_email,
        user_id=user_id,
        user_message=request.user_message
    )
    
    return {"task_id": task.id}


@router.get("/feedbacks", response_model=GetLLMFeedbackResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_gpt_feedback(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    GPT의 피드백을 생성하는 API
    
    현재 대화 내역을 분석하여 사용자의 응답에 대한 비판적 피드백을 생성합니다.
    Celery 태스크를 비동기로 실행하고 task_id를 반환합니다.
    """
    # User 조회하여 email 가져오기
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user_email = user.email
    
    # Celery Task 실행
    task = get_gpt_feedback.delay(user_email)
    
    return {"task_id": task.id}


@router.get("/results", response_model=GetLLMResultResponse, status_code=status.HTTP_200_OK)
async def request_gpt_result(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    대화 종료 시 피드백을 출력하고 저장하는 API
    
    Redis에서 room_id를 가져오고, GPT 결과를 생성하여 데이터베이스에 저장한 후 반환합니다.
    """
    # User 조회하여 email 가져오기
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user_email = user.email
    
    # Redis에서 room_id 가져오기
    room_id_key = f"room_id:{user_email}"
    room_id = await redis_client.get(room_id_key)
    
    if room_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="room_id not found in Redis"
        )
    
    # room_id를 int로 변환 (예외 처리 포함)
    try:
        room_id = int(room_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room_id in Redis"
        )
    
    # GPT 결과 요청 (Celery 태스크를 비동기로 실행)
    task = get_gpt_result.apply_async(args=[user_email])
    result_text = await run_in_threadpool(task.get)
    
    # 데이터베이스에 피드백 저장 (소유자 검증 포함)
    chat_room_updated = ChatRoomRepository.update_result(db, room_id, user_id, result_text)
    if not chat_room_updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    # Redis에서 사용자 관련 키 명시적으로 삭제 (성능 최적화)
    keys_to_delete = [
        f"room_id:{user_email}",
        f"episode_id:{user_email}",
        f"count:{user_email}",
        f"character_id:{user_email}",
        f"feedbacks:{user_email}",
        f"talk_content:{user_email}",
        f"memory_episode:{user_email}",
    ]
    # 존재하는 키만 삭제
    for key in keys_to_delete:
        if await redis_client.exists(key):
            await redis_client.delete(key)
    
    return {
        "result": result_text,
        "name": user.name,
        "room_id": room_id
    }



