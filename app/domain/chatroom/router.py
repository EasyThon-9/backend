from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.domain.chatroom.schemas import (
    SaveChatMessageRequest,
    SaveChatMessageResponse,
    ChatRoomListResponse,
    ChatHistoryResponse,
    ChatRoomListItem,
    ChatMessageItem
)
from app.domain.chatroom.repository import ChatRoomRepository, ChatMessageRepository
from app.domain.chatroom.model import MessageType
from app.core.dependencies import get_db
from app.core.security import get_current_user_id

router = APIRouter()


@router.post("/messages", response_model=SaveChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def save_chat_message(
    request: SaveChatMessageRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    채팅 내역 저장 API
    
    사용자 또는 어시스턴트의 메시지를 데이터베이스에 저장합니다.
    """
    
    # 채팅방 소유자 확인
    room = ChatRoomRepository.get_by_id_and_user_id(db, request.chat_room_id, user_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found or you don't have permission"
        )
    
    # message_type 검증 및 변환
    try:
        message_type = MessageType(request.message_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message_type. Must be 'user' or 'assistant'"
        )
    
    # 메시지 저장
    message = ChatMessageRepository.create(
        db=db,
        chat_room_id=request.chat_room_id,
        message_type=message_type,
        content=request.content
    )
    
    return SaveChatMessageResponse(
        id=message.id,
        chat_room_id=message.chat_room_id,
        message_type=message.message_type.value,
        content=message.content,
        created_at=message.created_at
    )


@router.get("/rooms", response_model=ChatRoomListResponse, status_code=status.HTTP_200_OK)
async def get_chat_rooms(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    채팅 목록 조회 API
    
    현재 사용자의 모든 채팅방 목록을 최신순으로 반환합니다.
    """
    
    rooms = ChatRoomRepository.get_user_rooms(db, user_id)
    
    room_items = [
        ChatRoomListItem(
            id=room.id,
            user_id=room.user_id,
            character_id=room.character_id,
            result=room.result,
            created_at=room.created_at,
            updated_at=room.updated_at
        )
        for room in rooms
    ]
    
    return ChatRoomListResponse(rooms=room_items)


@router.get("/rooms/{room_id}/messages", response_model=ChatHistoryResponse, status_code=status.HTTP_200_OK)
async def get_chat_history(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    채팅 내역 조회 API
    
    특정 채팅방의 모든 메시지를 시간순으로 반환합니다.
    """
    
    # 채팅방 소유자 확인 및 메시지 조회
    messages = ChatMessageRepository.get_by_room_id_and_user_id(db, room_id, user_id)
    
    if not messages:
        # 채팅방이 존재하는지 확인
        room = ChatRoomRepository.get_by_id_and_user_id(db, room_id, user_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat room not found or you don't have permission"
            )
    
    message_items = [
        ChatMessageItem(
            id=message.id,
            chat_room_id=message.chat_room_id,
            message_type=message.message_type.value,
            content=message.content,
            created_at=message.created_at
        )
        for message in messages
    ]
    
    return ChatHistoryResponse(
        chat_room_id=room_id,
        messages=message_items
    )

