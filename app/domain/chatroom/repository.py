from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.domain.chatroom.model import ChatRoom, ChatMessage, MessageType
from typing import Optional, List


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
    def get_by_id_and_user_id(db: Session, room_id: int, user_id: int) -> Optional[ChatRoom]:
        """ID와 사용자 ID로 채팅방 조회 (소유자 확인용)"""
        return db.query(ChatRoom).filter(
            and_(
                ChatRoom.id == room_id,
                ChatRoom.user_id == user_id
            )
        ).first()
    
    @staticmethod
    def get_user_rooms(db: Session, user_id: int) -> List[ChatRoom]:
        """사용자의 모든 채팅방 조회 (최신순)"""
        return db.query(ChatRoom).filter(
            ChatRoom.user_id == user_id
        ).order_by(desc(ChatRoom.created_at)).all()
    
    @staticmethod
    def delete_result(db: Session, room_id: int) -> bool:
        """채팅방 결과 삭제"""
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if room:
            room.result = ""
            db.commit()
            return True
        return False
    
    @staticmethod
    def update_result(db: Session, room_id: int, user_id: int, result: str) -> bool:
        """채팅방 결과 업데이트 (소유자 검증 포함)"""
        room = db.query(ChatRoom).filter(
            and_(ChatRoom.id == room_id, ChatRoom.user_id == user_id)
        ).first()
        if room:
            room.result = result
            db.commit()
            db.refresh(room)
            return True
        return False


class ChatMessageRepository:
    """ChatMessage 도메인 데이터베이스 접근 레이어"""
    
    @staticmethod
    def create(
        db: Session, 
        chat_room_id: int, 
        message_type: MessageType, 
        content: str
    ) -> ChatMessage:
        """채팅 메시지 생성"""
        message = ChatMessage(
            chat_room_id=chat_room_id,
            message_type=message_type,
            content=content
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    @staticmethod
    def get_by_room_id(db: Session, chat_room_id: int) -> List[ChatMessage]:
        """채팅방의 모든 메시지 조회 (시간순)"""
        return db.query(ChatMessage).filter(
            ChatMessage.chat_room_id == chat_room_id
        ).order_by(ChatMessage.created_at).all()
    
    @staticmethod
    def get_by_room_id_and_user_id(
        db: Session, 
        chat_room_id: int, 
        user_id: int
    ) -> List[ChatMessage]:
        """채팅방의 모든 메시지 조회 (소유자 확인 포함)"""
        # 채팅방이 사용자 소유인지 확인
        room = ChatRoomRepository.get_by_id_and_user_id(db, chat_room_id, user_id)
        if not room:
            return []
        
        return db.query(ChatMessage).filter(
            ChatMessage.chat_room_id == chat_room_id
        ).order_by(ChatMessage.created_at).all()

