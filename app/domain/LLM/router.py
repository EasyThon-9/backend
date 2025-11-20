from fastapi import APIRouter, Depends, status
from app.domain.LLM.schemas import GetLLMMessageRequest, GetLLMMessageResponse
from app.domain.LLM.task import get_llm_message
from app.core.redis import get_redis_pool

router = APIRouter()

def get_current_user_info():
    return {"email": "testuser@example.com", "id": 1}

@router.post("/message", response_model=GetLLMMessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_llm_message(
    request: GetLLMMessageRequest,
    user_info: dict = Depends(get_current_user_info) # Auth Dependency Injection
):
    user_email = user_info["email"]
    user_id = user_info["id"]
    
    # 비동기 Redis 사용
    redis_client = await get_redis_pool()
    try:
        # episode_id 저장
        episode_key = f"episode_id:{user_email}"
        if await redis_client.exists(episode_key):
            await redis_client.delete(episode_key)
        await redis_client.set(episode_key, request.episode_id)
        
        # count 증가
        count_key = f"count:{user_email}"
        if await redis_client.exists(count_key):
            await redis_client.incr(count_key)
        else:
            await redis_client.set(count_key, 1)
            
        # character_id 저장 (테스트 코드 참조)
        char_key = f"character_id:{user_email}"
        await redis_client.set(char_key, request.character_id)
        
    finally:
        await redis_client.close()

    # 2. Celery Task 실행
    task = get_llm_message.delay(
        character_id=request.character_id, 
        episode_id=request.episode_id, 
        user_email=user_email,
        user_id=user_id
    )
    
    return {"task_id": task.id}



