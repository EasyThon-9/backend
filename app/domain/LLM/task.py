from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.redis import get_sync_redis
from app.core.config import settings
from app.domain.character.model import CharacterInfo
from app.domain.episode.model import Episode
import openai
import json
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# OpenAI API 키 설정
openai.api_key = settings.LLM_API_KEY

@celery_app.task
def get_llm_message(character_id: int, episode_id: int, user_email: str, user_id: int):
    db = SessionLocal()
    redis_client = get_sync_redis()
    
    try:
        # DB 조회
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        character = db.query(CharacterInfo).filter(CharacterInfo.id == character_id).first()
        
        if not episode or not character:
            raise ValueError(f"Data not found for episode_id={episode_id} or character_id={character_id}")

        episode_content = episode.content
        character_script = character.script

        # OpenAI Streaming 호출
        stream = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"""
                        You are character with {character_script} when a subordinate who is dealing with is {episode_content}.\
                        What are you going to say in this situation?\
                        You must provide answer in Korean.\
                        Generate answers in 40 Korean characters.\
                    """, # 프롬프트 축약 (원본 그대로 사용하시면 됩니다)
                },
            ],
            stream=True,
        )

        # Redis 키 정리
        if redis_client.exists(f"episode_id:{user_email}"):
            redis_client.delete(f"episode_id:{user_email}")
        
        if redis_client.exists(f"talk_content:{user_email}"):
            redis_client.delete(f"talk_content:{user_email}")

        # 스트리밍 응답 처리 및 Redis Publish
        full_response = ""
        for response in stream:
            if "delta" in response.choices[0] and "content" in response.choices[0]["delta"]:
                chunk = response.choices[0]["delta"]["content"]
                full_response += chunk
                
                # Redis 채널로 직접 발행
                channel_name = f"chat_{user_id}"
                message_data = {
                    "type": "llm_talk_message",
                    "message": chunk
                }
                redis_client.publish(channel_name, json.dumps(message_data))

        # 결과 저장 (Redis)
        redis_client.set(f"talk_content:{user_email}", full_response)

        # TTS 로직 추가 예정

        return full_response

    except Exception as e:
        logger.error(f"Error in get_llm_message task: {e}", exc_info=True)
        raise
    finally:
        if redis_client:
            redis_client.close()
        db.close()

