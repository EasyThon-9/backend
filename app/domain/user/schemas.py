from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegistrationRequest(BaseModel):
    """회원가입 요청 스키마"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")
    name: str = Field(..., min_length=1, max_length=255, description="이름")


class UserRegistrationResponse(BaseModel):
    """회원가입 응답 스키마"""
    message: str


class LoginRequest(BaseModel):
    """로그인 요청 스키마"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """토큰 응답 스키마"""
    message: str
    access_token: str
    refresh_token: str


class LogoutRequest(BaseModel):
    """로그아웃 요청 스키마"""
    refresh_token: str


class LogoutResponse(BaseModel):
    """로그아웃 응답 스키마"""
    message: str


class EmailCheckResponse(BaseModel):
    """이메일 중복 확인 응답 스키마"""
    message: str


class ResultItem(BaseModel):
    """결과 아이템 스키마"""
    room_id: int
    character_id: int
    name: str
    image_url: Optional[str] = None


class UserResultResponse(BaseModel):
    """사용자 결과 조회 응답 스키마"""
    status: str
    message: str
    data: list[ResultItem]


class UserDetailResultResponse(BaseModel):
    """사용자 결과 상세 조회 응답 스키마"""
    status: str
    message: str
    room_id: int
    name: str
    result: str
    image_url: Optional[str] = None

