from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.common.model import TimestampMixin

class CharacterInfo(Base, TimestampMixin):
    __tablename__ = "character_info"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20))
    script = Column(String(1000)) # 성격 스크립트

    # Voice와의 관계 설정 (1:N)
    voices = relationship("Voice", back_populates="character")

class Voice(Base, TimestampMixin): # Voice는 타임스탬프가 굳이 필요 없다면 상속 안 해도 됨 (선택)
    __tablename__ = "voice"

    id = Column(String(200), primary_key=True) # ERD상 varchar(200)이 PK
    character_id = Column(Integer, ForeignKey("character_info.id"))
    stability = Column(Integer)
    similarity = Column(Integer)
    style = Column(Integer)
    user_speaker_boost = Column(Boolean)

    character = relationship("CharacterInfo", back_populates="voices")