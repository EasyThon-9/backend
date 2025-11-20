from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.common.model import TimestampMixin

class Episode(Base, TimestampMixin):
    __tablename__ = "episode"

    id = Column(Integer, primary_key=True, index=True)
    episode_time_id = Column(Integer, ForeignKey("episode_time.id"))
    content = Column(String(200))

    episode_time = relationship("EpisodeTime", back_populates="episodes")

class EpisodeTime(Base, TimestampMixin):
    __tablename__ = "episode_time"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(String(200)) # 예: "오전 10시", "저녁" 등

    episodes = relationship("Episode", back_populates="episode_time")