from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
import redis.asyncio as redis

from app.core.database import SessionLocal
from app.core.redis import get_redis_pool
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_id
)
from app.domain.user import schemas
from app.domain.user.service import UserService
from app.domain.user.repository import UserRepository, ChatRoomRepository
from app.domain.user.model import User
from app.domain.chatroom.model import ChatRoom

router = APIRouter()


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_redis_client() -> redis.Redis:
    """Redis 클라이언트 의존성"""
    redis_client = await get_redis_pool()
    try:
        yield redis_client
    finally:
        await redis_client.aclose()


@router.post(
    "/register",
    response_model=schemas.UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="새로운 사용자를 등록합니다."
)
async def register_user(
    request: schemas.UserRegistrationRequest,
    db: Session = Depends(get_db)
):
    """회원가입 API"""
    try:
        user = UserService.register_user(
            db=db,
            email=request.email,
            password=request.password,
            name=request.name
        )
        return schemas.UserRegistrationResponse(
            message="회원가입에 성공하였습니다."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get(
    "/check-email",
    response_model=schemas.EmailCheckResponse,
    summary="이메일 중복 확인",
    description="이메일이 이미 사용 중인지 확인합니다."
)
async def check_email(
    email: str = Query(..., description="중복 확인할 이메일"),
    db: Session = Depends(get_db)
):
    """이메일 중복 확인 API"""
    if UserService.check_email_exists(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 이메일입니다"
        )
    
    return schemas.EmailCheckResponse(
        message="사용 가능한 이메일입니다"
    )


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    summary="로그인",
    description="이메일과 비밀번호로 로그인하고 토큰을 발급받습니다."
)
async def login(
    request: schemas.LoginRequest,
    db: Session = Depends(get_db)
):
    """로그인 API"""
    user = UserService.authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다"
        )
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return schemas.TokenResponse(
        message="로그인에 성공하였습니다.",
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post(
    "/logout",
    response_model=schemas.LogoutResponse,
    status_code=status.HTTP_205_RESET_CONTENT,
    summary="로그아웃",
    description="리프레시 토큰을 무효화하여 로그아웃합니다."
)
async def logout(
    request: schemas.LogoutRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """로그아웃 API"""
    if not request.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="리프레시 토큰이 필요합니다."
        )
    
    try:
        # Refresh 토큰 검증
        refresh_payload = decode_token(request.refresh_token, "refresh")
        
        # Refresh 토큰에서 사용자 ID 추출
        refresh_sub = refresh_payload.get("sub")
        if not refresh_sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token: subject not found."
            )
        
        try:
            refresh_user_id: int = int(refresh_sub)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token: subject must be an integer."
            )
        
        # Access Token의 사용자 ID와 Refresh Token의 사용자 ID 일치 확인
        if refresh_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="토큰 소유자가 일치하지 않습니다."
            )
        
        # 사용자 정보 가져오기
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # Refresh 토큰 만료 시간 계산 (블랙리스트 TTL용)
        exp = refresh_payload.get("exp")
        if exp:
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - current_time)
            if ttl > 0:
                # Refresh 토큰을 블랙리스트에 추가
                blacklist_key = f"blacklist:refresh:{request.refresh_token}"
                await redis_client.setex(blacklist_key, ttl, "1")
        
        # Redis에서 사용자 관련 키 삭제
        async for key in redis_client.scan_iter(match=f"*{user.email}*"):
            await redis_client.delete(key)
        
        return schemas.LogoutResponse(
            message="로그아웃되었습니다."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="로그아웃 처리 중 오류가 발생했습니다."
        )


@router.get(
    "/results",
    response_model=schemas.UserResultResponse,
    summary="사용자 결과 조회",
    description="사용자의 대화 결과 목록을 조회합니다."
)
async def get_user_results(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """사용자의 대화 결과 조회 API"""
    chat_rooms = ChatRoomRepository.get_user_result_rooms(db, user_id)
    
    if not chat_rooms:
        return schemas.UserResultResponse(
            status="200",
            message="채팅방을 찾을 수 없습니다.",
            data=[]
        )
    
    # 사용자 정보 가져오기
    user = UserRepository.get_by_id(db, user_id)
    user_name = user.name if user else ""
    
    result_items = [
        schemas.ResultItem(
            room_id=room.id,
            character_id=room.character_id,
            name=user_name,
        )
        for room in chat_rooms
    ]
    
    return schemas.UserResultResponse(
        status="200",
        message="결과 조회 성공",
        data=result_items
    )


@router.get(
    "/results/{room_id}",
    response_model=schemas.UserDetailResultResponse,
    summary="결과 상세 조회",
    description="특정 채팅방의 결과를 상세 조회합니다."
)
async def get_user_detail_result(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """사용자 결과 상세 조회 API"""
    room = ChatRoomRepository.get_by_id_and_user_id(db, room_id, user_id)
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="채팅방을 찾을 수 없습니다."
        )
    
    # 사용자 정보 가져오기
    user = UserRepository.get_by_id(db, user_id)
    user_name = user.name if user else ""

    return schemas.UserDetailResultResponse(
        status="200",
        message="결과 조회 성공",
        room_id=room.id,
        name=user_name,
        result=room.result or "",
    )


@router.delete(
    "/results/{room_id}",
    response_model=dict,
    summary="결과 삭제",
    description="특정 채팅방의 결과를 삭제합니다."
)
async def delete_user_result(
    room_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """결과 삭제 API"""
    room = ChatRoomRepository.get_by_id_and_user_id(db, room_id, user_id)
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="채팅방을 찾을 수 없습니다."
        )
    
    success = ChatRoomRepository.delete_result(db, room_id)
    
    if success:
        return {"status": "200", "message": "삭제 성공"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="삭제 처리 중 오류가 발생했습니다."
        )
