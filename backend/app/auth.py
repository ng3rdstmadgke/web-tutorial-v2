"""認証関連のユーティリティ。

本章ではパスワードのハッシュ化・検証だけを実装する。
JWT 発行・検証などは Chapter 6 で追加する。
"""
from pwdlib import PasswordHash


# Argon2 を推奨設定で使う PasswordHash インスタンス
_password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """平文パスワードを Argon2 でハッシュ化する"""
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """平文パスワードがハッシュと一致するかを検証する"""
    return _password_hash.verify(plain_password, hashed_password)