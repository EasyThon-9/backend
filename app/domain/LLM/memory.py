from threading import RLock
from typing import Dict, List

from langchain.memory import ConversationBufferMemory
from langchain.schema import AIMessage, HumanMessage

_memory_store: Dict[str, ConversationBufferMemory] = {}
_memory_lock = RLock()


def get_user_memory(user_email: str) -> ConversationBufferMemory:
    """사용자별 대화 메모리를 반환 (없으면 생성)"""
    with _memory_lock:
        if user_email not in _memory_store:
            _memory_store[user_email] = ConversationBufferMemory(return_messages=True)
        return _memory_store[user_email]


def reset_user_memory(user_email: str) -> None:
    """사용자 메모리를 초기화"""
    with _memory_lock:
        if user_email in _memory_store:
            _memory_store[user_email].chat_memory.clear()
            del _memory_store[user_email]


def build_conversation_history(user_email: str) -> List[dict]:
    """OpenAI ChatCompletion 포맷으로 변환된 대화 기록 반환"""
    with _memory_lock:
        memory = _memory_store.get(user_email)
        if not memory:
            return []

        history: List[dict] = []
        for message in memory.chat_memory.messages:
            if isinstance(message, HumanMessage):
                history.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})
        return history


def append_memory(user_email: str, user_message: str, assistant_message: str) -> None:
    """대화 한 턴을 LangChain 메모리에 추가"""
    with _memory_lock:
        memory = get_user_memory(user_email)
        memory.chat_memory.add_user_message(user_message)
        memory.chat_memory.add_ai_message(assistant_message)

