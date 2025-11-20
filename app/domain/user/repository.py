from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.domain.user.model import User
from app.domain.chatroom.model import ChatRoom
from typing import Optional


class UserRepository:
    """User 도메인 데이터베이스 접근 레이어"""
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def create(db: Session, email: str, hashed_password: str, name: str) -> User:
        """새 사용자 생성"""
        user = User(email=email, password=hashed_password, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def exists_by_email(db: Session, email: str) -> bool:
        """이메일 중복 확인"""
        return db.query(User).filter(User.email == email).first() is not None
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        return db.query(User).filter(User.id == user_id).first()


class ChatRoomRepository:
    """ChatRoom 도메인 데이터베이스 접근 레이어"""
    
    @staticmethod
    def get_user_result_rooms(db: Session, user_id: int):
        """사용자의 결과가 있는 채팅방 조회"""
        return db.query(ChatRoom).filter(
            and_(
                ChatRoom.user_id == user_id,
                ChatRoom.result != "",
                ChatRoom.result.isnot(None)
            )
        ).all()
    
    @staticmethod
    def get_by_id(db: Session, room_id: int) -> Optional[ChatRoom]:
        """ID로 채팅방 조회"""
        return db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    
    @staticmethod
    def delete_result(db: Session, room_id: int) -> bool:
        """채팅방 결과 삭제"""
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if room:
            room.result = ""
            db.commit()
            return True
        return False

