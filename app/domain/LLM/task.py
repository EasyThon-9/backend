from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.redis import get_sync_redis
from app.core.config import settings
from app.domain.character.model import CharacterInfo
from app.domain.episode.model import Episode
from app.domain.user.model import User
from app.domain.LLM.memory import (
    append_memory,
    build_conversation_history,
    get_user_memory,
    reset_user_memory,
)
import openai
import json
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# OpenAI API 키 설정
openai.api_key = settings.LLM_API_KEY

@celery_app.task
def get_llm_message(
    character_id: int,
    episode_id: int,
    user_email: str,
    user_id: int,
    user_message: str,
):
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

        # LangChain 메모리 준비 (에피소드 변경 시 초기화)
        memory_episode_key = f"memory_episode:{user_email}"
        stored_episode_id = redis_client.get(memory_episode_key)
        if stored_episode_id != str(episode_id):
            reset_user_memory(user_email)
            redis_client.set(memory_episode_key, episode_id)
        get_user_memory(user_email)  # 메모리 초기화 보장

        conversation_history = build_conversation_history(user_email)
        prompt_messages = [
            {
                "role": "system",
                "content": (
                    f"You are character with {character_script} when a subordinate who is dealing with is {episode_content}. "
                    "What are you going to say in this situation? "
                    "You must provide answer in Korean. "
                    "Generate answers in 40 Korean characters."
                ),
            },
            *conversation_history,
        ]

        if user_message:
            prompt_messages.append({"role": "user", "content": user_message})

        # OpenAI Streaming 호출
        stream = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=prompt_messages,
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

        # LangChain 메모리에 대화 내용 저장
        if user_message and full_response:
            append_memory(user_email, user_message, full_response)

        # TTS 로직 추가 예정

        return full_response

    except Exception as e:
        logger.error(f"Error in get_llm_message task: {e}", exc_info=True)
        raise
    finally:
        if redis_client:
            redis_client.close()
        db.close()


@celery_app.task
def get_gpt_feedback(user_email: str):
    """
    사용자의 대화 내역을 분석하여 피드백을 생성하는 Celery 태스크
    
    Args:
        user_email: 사용자 이메일
    
    Returns:
        str: 생성된 피드백 텍스트
    """
    db = SessionLocal()
    redis_client = get_sync_redis()
    
    try:
        # DB에서 사용자 정보 조회
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise ValueError(f"User not found for email: {user_email}")
        
        user_id = user.id
        
        # Redis에서 episode_id와 character_id 조회
        episode_id = redis_client.get(f"episode_id:{user_email}")
        if not episode_id:
            raise ValueError(f"episode_id not found in Redis for user: {user_email}")
        
        episode_id = int(episode_id.decode() if isinstance(episode_id, bytes) else episode_id)
        
        character_id = redis_client.get(f"character_id:{user_email}")
        if not character_id:
            # 기본값으로 6번(김수미) 사용
            character_id = 6
        else:
            character_id = int(character_id.decode() if isinstance(character_id, bytes) else character_id)
        
        # DB 조회
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        character = db.query(CharacterInfo).filter(CharacterInfo.id == character_id).first()
        
        if not episode or not character:
            raise ValueError(f"Data not found for episode_id={episode_id} or character_id={character_id}")
        
        episode_content = episode.content
        character_script = character.script
        
        # LangChain 메모리에서 대화 내역 가져오기
        conversation_history = build_conversation_history(user_email)
        
        # 대화 내역을 문자열로 변환 (프롬프트에 사용하기 위해)
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_history
        ])
        
        # GPT-4o로 피드백 생성
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"""
                    conversation : {conversation_text}
                    You are character with {character_script}. In {episode_content}, Look at this conversation and give the feedback.\
                    Give me feedback on the answer\
                    You must give feedback only to user's answer.\
                    Feedback means scolding a person for what he or she did well and what he or she didn't do in his or her answer and telling him or her how to say it.\
                    You have to give "user" a stinging piece of advice in that conversation\
                    You need to see the answer of "user" in that conversation and give feedback.\
                    You have to speak strongly so that you can come to your senses.\
                    You must provide answer in Korean.\
                    Don't generate the questions given earlier, just generate the answers.\
                    When you generating an answer, don't explain the answer or question in advance, just create an answer.\
                    Generate answers in 90 Korean characters.\
                    When you answer, don't use numbers like 1, 2, 3 and use conjunctions to make the flow of the text natural.\
                    """
                },
            ],
        )
        
        result = response.choices[0].message["content"].strip()
        
        # Redis에 피드백 저장 (List 사용)
        redis_key = f"feedbacks:{user_email}"
        redis_client.rpush(redis_key, result)
        
        # Redis pub/sub으로 피드백 전송
        channel_name = f"chat_{user_id}"
        message_data = {
            "type": "gpt_feedback_message",
            "message": result,
        }
        redis_client.publish(channel_name, json.dumps(message_data))
        
        # TTS 로직 추가 예정
        # text_to_speech_file(result, character_id, user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_gpt_feedback task: {e}", exc_info=True)
        raise
    finally:
        if redis_client:
            redis_client.close()
        db.close()


@celery_app.task
def get_gpt_result(user_email: str):
    """
    모든 피드백을 종합하여 최종 결과를 생성하는 Celery 태스크
    
    Args:
        user_email: 사용자 이메일
    
    Returns:
        str: 생성된 최종 피드백 텍스트
    """
    db = SessionLocal()
    redis_client = get_sync_redis()
    
    try:
        # Redis에서 character_id 조회
        character_id = redis_client.get(f"character_id:{user_email}")
        if not character_id:
            # 기본값으로 6번(김수미) 사용
            character_id = 6
        else:
            character_id = int(character_id.decode() if isinstance(character_id, bytes) else character_id)
        
        # DB에서 캐릭터 정보 조회
        character = db.query(CharacterInfo).filter(CharacterInfo.id == character_id).first()
        if not character:
            raise ValueError(f"Character not found for character_id={character_id}")
        
        character_script = character.script
        
        # Redis에서 모든 피드백 가져오기 (List 사용)
        feedback_key = f"feedbacks:{user_email}"
        feedback_values = redis_client.lrange(feedback_key, 0, -1)
        
        if not feedback_values:
            raise ValueError(f"No feedbacks found for user: {user_email}")
        
        # 바이트를 문자열로 변환 (필요한 경우)
        feedback_values = [
            value.decode() if isinstance(value, bytes) else value
            for value in feedback_values
        ]
        feedback_values_str = ", ".join(feedback_values)
        
        # GPT-4o로 최종 피드백 생성
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"""
                    You are character with {character_script}.
                    {feedback_values_str}, Look at those feedbacks and write the final feedback.\
                    Feedback means scolding a person for what he or she did well and what he or she didn't do in his or her answer and telling him or her how to say it.\
                    You must provide answer in Korean.\
                    You must never use profanity.\
                    Don't generate the questions given earlier, just generate the answers.\
                    When you generating an answer, don't explain the answer or question in advance, just create an answer.\
                    Generate answers in 300 Korean characters.\
                    When you answer, don't use numbers like 1, 2, 3 and use conjunctions to make the flow of the text natural.\
                    """
                },
            ],
        )
        
        result = response.choices[0].message["content"].strip()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_gpt_result task: {e}", exc_info=True)
        raise
    finally:
        if redis_client:
            redis_client.close()
        db.close()

