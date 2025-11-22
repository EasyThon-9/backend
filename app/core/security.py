from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호를 검증합니다."""
    # None 체크 및 타입 검증
    if plain_password is None or not isinstance(plain_password, str):
        return False
    
    # Bcrypt는 최대 72바이트까지만 처리 가능하므로 자르기
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        plain_password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호를 해시화합니다."""
    # None 체크
    if password is None:
        raise ValueError("Password cannot be None")
    
    # 문자열 타입 강제 검증 (객체가 전달되면 에러 발생)
    if not isinstance(password, str):
        raise TypeError(f"Password must be a string, got {type(password).__name__}")
    
    # 빈 문자열 체크
    if len(password) == 0:
        raise ValueError("Password cannot be empty")
    
    # Bcrypt는 최대 72바이트까지만 처리 가능
    # UTF-8 인코딩 기준으로 바이트 수 계산
    password_bytes = password.encode('utf-8')
    
    # 72바이트를 초과하면 반드시 자르기 (passlib의 요구사항)
    # passlib은 72바이트를 초과하면 ValueError를 발생시키므로, 미리 처리해야 함
    if len(password_bytes) > 72:
        # 72바이트로 자르기
        password_bytes = password_bytes[:72]
        # 다시 문자열로 디코딩
        password = password_bytes.decode('utf-8', errors='replace')
        # 재확인: 디코딩 후 다시 인코딩했을 때도 72바이트 이하인지 확인
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # 한 글자씩 줄여가며 72바이트 이하로 만들기
            while len(password.encode('utf-8')) > 72 and len(password) > 0:
                password = password[:-1]
            password_bytes = password.encode('utf-8')[:72]
    
    # 최종 확인: 반드시 72바이트 이하로 보장
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # passlib의 hash 함수에 bytes를 직접 전달하여 더 안전하게 처리
    # passlib은 문자열과 bytes 모두를 받을 수 있지만, bytes로 전달하면 더 명확함
    # bytes로 전달하면 passlib이 내부적으로 문자열로 변환하는 과정에서 길이가 늘어나는 것을 방지
    try:
        # bytes를 문자열로 변환하여 전달 (passlib이 내부적으로 처리)
        password_str = password_bytes.decode('utf-8', errors='replace')
        return pwd_context.hash(password_str)
    except (ValueError, TypeError) as e:
        # 에러 처리: 72바이트 관련 에러인 경우
        error_msg = str(e).lower()
        if "72" in error_msg or "bytes" in error_msg or "longer" in error_msg:
            # 더 짧게 자르기 (60바이트로 안전하게)
            safe_bytes = password_bytes[:60]
            password_str = safe_bytes.decode('utf-8', errors='replace')
            try:
                return pwd_context.hash(password_str)
            except Exception:
                # 최후의 수단: 50바이트로 자르기
                safe_bytes = password_bytes[:50]
                password_str = safe_bytes.decode('utf-8', errors='replace')
                return pwd_context.hash(password_str)
        raise


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Access Token을 생성합니다."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Refresh Token을 생성합니다."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str, token_type: str = "access") -> dict:
    """JWT 토큰을 디코딩하고 검증합니다."""
    try:
        secret_key = settings.SECRET_KEY if token_type == "access" else settings.REFRESH_SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        
        # 토큰 타입 검증
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """현재 인증된 사용자의 ID를 반환합니다."""
    token = credentials.credentials
    payload = decode_token(token, "access")
    
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: subject not found."
        )
    
    try:
        user_id: int = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: subject must be an integer."
        )
    
    return user_id