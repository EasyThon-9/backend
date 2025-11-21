from fastapi import APIRouter, Depends, status
from app.domain.LLM.schemas import (
    GetLLMMessageRequest, 
    GetLLMMessageResponse,
    GetLLMFeedbackResponse,
    GetLLMResultResponse
)
from app.domain.LLM.task import get_llm_message, get_gpt_feedback, get_gpt_result
from app.core.redis import get_redis_pool
import redis.asyncio as redis

router = APIRouter()

def get_current_user_info():
    return {"email": "testuser@example.com", "id": 1}

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
    user_info: dict = Depends(get_current_user_info), # Auth Dependency Injection
    redis_client: redis.Redis = Depends(get_redis_client)
):
    user_email = user_info["email"]
    user_id = user_info["id"]
    
    # episode_id 저장
    episode_key = f"episode_id:{user_email}"
    if await redis_client.exists(episode_key):
        await redis_client.delete(episode_key)
    await redis_client.set(episode_key, request.episode_id)
    
    # count 증가 (INCR은 키가 없을 경우 0으로 초기화 후 1 증가)
    count_key = f"count:{user_email}"
    await redis_client.incr(count_key)
        
    # character_id 저장 (테스트 코드 참조)
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
    user_info: dict = Depends(get_current_user_info), # Auth Dependency Injection
):
    """
    GPT의 피드백을 생성하는 API
    
    현재 대화 내역을 분석하여 사용자의 응답에 대한 비판적 피드백을 생성합니다.
    Celery 태스크를 비동기로 실행하고 task_id를 반환합니다.
    """
    user_email = user_info["email"]
    
    # Celery Task 실행
    task = get_gpt_feedback.delay(user_email)
    
    return {"task_id": task.id}


@router.get("/results", response_model=GetLLMResultResponse, status_code=status.HTTP_200_OK)
def request_gpt_result(
    user_info: dict = Depends(get_current_user_info), # Auth Dependency Injection
):
    """
    GPT의 최종 피드백을 가져오는 API
    
    모든 피드백을 종합하여 최종 결과를 생성하고 반환합니다.
    """
    user_email = user_info["email"]
    
    response_text = get_gpt_result(user_email)
    
    return {"result": response_text}



