# auth.py
# 로그인 처리를 담당하는 파일
#
# - NARO는 개인용 서비스라서 회원가입 없이 계정 1개만 사용한다.
# - 비밀번호는 원문 그대로 저장하지 않고, 해시(hash)로 바꿔서 저장한다.
# - 로그인에 성공하면 임의의 문자열(토큰)을 발급하고, 이후 요청마다 토큰을 확인한다.

import hashlib
import os
import secrets

from fastapi import Header, HTTPException

from database import SessionLocal, User

# 로그인한 사용자의 토큰 목록 (서버가 재시작되면 비워지므로 다시 로그인해야 한다)
active_tokens = set()


def hash_password(password, salt):
    """비밀번호 + 소금(salt)을 10만 번 해시해서 원래 비밀번호를 알아낼 수 없게 만든다"""
    result = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return result.hex()


def create_default_user():
    """서버 시작 시 계정이 없으면 .env에 적힌 아이디/비밀번호로 계정을 만든다"""
    db = SessionLocal()
    try:
        if db.query(User).first() is None:
            username = os.getenv("NARO_USERNAME", "naro")
            password = os.getenv("NARO_PASSWORD", "naro1234")
            salt = secrets.token_hex(16)
            db.add(User(username=username, password_hash=hash_password(password, salt), salt=salt))
            db.commit()
            print(f"[NARO] 계정 '{username}'을(를) 만들었습니다.")
    finally:
        db.close()


def login(username, password):
    """아이디/비밀번호가 맞으면 새 토큰을 돌려주고, 틀리면 None을 돌려준다"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            return None
        # 입력한 비밀번호를 같은 방법으로 해시해서 저장된 해시와 비교한다
        if hash_password(password, user.salt) != user.password_hash:
            return None
        token = secrets.token_hex(32)
        active_tokens.add(token)
        return token
    finally:
        db.close()


def require_login(authorization: str = Header(default="")):
    """로그인이 필요한 API에 붙이는 검사 함수.
    요청 헤더 'Authorization: Bearer 토큰'의 토큰이 유효한지 확인한다."""
    token = authorization.replace("Bearer ", "")
    if token not in active_tokens:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return token
