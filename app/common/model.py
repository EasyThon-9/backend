# app/common/mixins.py
from sqlalchemy import Column, DateTime, func
from datetime import datetime

class TimestampMixin:

    # 생성 시간
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # 수정 시간 
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # 삭제 시간 
    deleted_at = Column(DateTime, nullable=True)