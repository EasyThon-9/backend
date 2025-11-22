from typing import List

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain.schema import AIMessage, HumanMessage

from app.core.config import settings


def _get_redis_history(user_email: str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(
        session_id=user_email,
        url=settings.CELERY_RESULT_BACKEND,
    )


def get_user_memory(user_email: str) -> ConversationBufferMemory:
    """Redis 기반 LangChain 메모리를 반환"""
    return ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=_get_redis_history(user_email),
        return_messages=True,
    )


def reset_user_memory(user_email: str) -> None:
    """사용자 메모리를 초기화"""
    history = _get_redis_history(user_email)
    history.clear()


def build_conversation_history(user_email: str) -> List[dict]:
    """OpenAI ChatCompletion 포맷으로 변환된 대화 기록 반환"""
    memory = get_user_memory(user_email)
    history: List[dict] = []
    for message in memory.chat_memory.messages:
        if isinstance(message, HumanMessage):
            history.append({"role": "user", "content": message.content})
        elif isinstance(message, AIMessage):
            history.append({"role": "assistant", "content": message.content})
    return history


def append_memory(user_email: str, user_message: str, assistant_message: str) -> None:
    """대화 한 턴을 LangChain 메모리에 추가"""
    memory = get_user_memory(user_email)
    memory.chat_memory.add_user_message(user_message)
    memory.chat_memory.add_ai_message(assistant_message)

