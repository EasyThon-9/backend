from sqlalchemy import Column, Integer, String, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.common.model import TimestampMixin
import enum

class MessageType(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ChatRoom(Base, TimestampMixin):
    __tablename__ = "chat_room"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer) # User 테이블이 있다면 ForeignKey 걸기
    character_id = Column(Integer, ForeignKey("character_info.id")) # 타 도메인 참조
    result = Column(String(2000))

    # ChatEpisode와의 관계
    chat_episodes = relationship("ChatEpisode", back_populates="chat_room")
    # ChatMessage와의 관계
    chat_messages = relationship("ChatMessage", back_populates="chat_room", cascade="all, delete-orphan")

class ChatEpisode(Base, TimestampMixin):
    __tablename__ = "chat_episode"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_room.id"))
    episode_id = Column(Integer, ForeignKey("episode.id")) # 타 도메인 참조

    chat_room = relationship("ChatRoom", back_populates="chat_episodes")

class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_message"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_room.id"), nullable=False)
    message_type = Column(SQLEnum(MessageType), nullable=False)
    content = Column(Text, nullable=False)

    chat_room = relationship("ChatRoom", back_populates="chat_messages")