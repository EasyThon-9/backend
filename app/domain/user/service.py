from sqlalchemy.orm import Session
from app.domain.user.repository import UserRepository, ChatRoomRepository
from app.domain.user.model import User
from app.core.security import verify_password, get_password_hash
from typing import Optional


class UserService:
    """User 도메인 비즈니스 로직 레이어"""
    
    @staticmethod
    def register_user(db: Session, email: str, password: str, name: str) -> User:
        """회원가입 처리"""
        # 이메일 중복 확인
        if UserRepository.exists_by_email(db, email):
            raise ValueError("이미 존재하는 이메일입니다")
        
        # 비밀번호 타입 및 None 검증
        if password is None:
            raise ValueError("비밀번호는 필수입니다")
        
        if not isinstance(password, str):
            raise ValueError(f"비밀번호는 문자열이어야 합니다. 현재 타입: {type(password)}")
        
        # 비밀번호 해시화 (get_password_hash에서 72바이트 제한 처리)
        hashed_password = get_password_hash(password)
        
        # 사용자 생성
        return UserRepository.create(db, email, hashed_password, name)
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """로그인 인증"""
        user = UserRepository.get_by_email(db, email)
        if not user:
            return None
        
        if not verify_password(password, user.password):
            return None
        
        return user
    
    @staticmethod
    def check_email_exists(db: Session, email: str) -> bool:
        """이메일 중복 확인"""
        return UserRepository.exists_by_email(db, email)

