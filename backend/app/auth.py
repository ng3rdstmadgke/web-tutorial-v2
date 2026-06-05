from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import env
from app.model import User
from app.session import get_session

# --- パスワードハッシュ ---

_password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """平文パスワードを Argon2 でハッシュ化する"""
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """平文パスワードがハッシュと一致するかを検証する"""
    return _password_hash.verify(plain_password, hashed_password)


# --- JWT ---

def create_access_token(username: str) -> str:
    """JWT アクセストークンを生成する"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=env.token_expire_minutes)
    payload = {
        "sub": username,  # subject: トークンの主体（ユーザー名）
        "exp": expire,    # expiration: 有効期限
    }
    return jwt.encode(payload, env.token_secret_key, algorithm=env.token_algorithm)


def decode_access_token(token: str) -> dict:
    """JWT を検証・デコードする。無効なら例外を投げる"""
    try:
        return jwt.decode(token, env.token_secret_key, algorithms=[env.token_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from None


# --- 認証ガード ---

def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """リクエストからトークンを取り出し、ユーザーを返す。

    トークンの取得元:
      1. Cookie の "access_token" (ブラウザ用)
      2. Authorization ヘッダの "Bearer <token>" (API クライアント用)
    """
    # 1. Cookie から取得を試みる
    token = request.cookies.get("access_token")

    # 2. Cookie が無ければ Authorization ヘッダから取得
    if token is None:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ")

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # トークンを検証してユーザーを取得
    payload = decode_access_token(token)
    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = session.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user