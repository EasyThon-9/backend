from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.domain.chatroom.model import MessageType


class SaveChatMessageRequest(BaseModel):
    chat_room_id: int
    message_type: str  # "user" or "assistant"
    content: str


class SaveChatMessageResponse(BaseModel):
    id: int
    chat_room_id: int
    message_type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRoomListItem(BaseModel):
    id: int
    user_id: int
    character_id: int
    result: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatRoomListResponse(BaseModel):
    rooms: List[ChatRoomListItem]


class ChatMessageItem(BaseModel):
    id: int
    chat_room_id: int
    message_type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    chat_room_id: int
    messages: List[ChatMessageItem]

