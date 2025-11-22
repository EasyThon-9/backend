from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.common.model import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200))
    password = Column(String(255))  # 해시값 저장을 위해 255로 변경
    name = Column(String(255))
