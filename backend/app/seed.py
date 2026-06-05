"""シードデータ（初期データ）を投入するスクリプト。

冪等に書くことで、何度実行してもエラーにならず、最終的に同じ状態になる。

実行方法:
    cd $PROJECT_DIR/backend
    uv run python -m app.seed
"""
from sqlalchemy import select

from app import auth
from app.model import Role, RoleType, User
from app.session import SessionLocal
from typing import TypedDict

class SeedUser(TypedDict):
    username: str
    password: str
    role: RoleType

def seed_roles() -> None:
    """roles テーブルに固定 3 件を投入する。すでに存在すれば何もしない。"""
    with SessionLocal() as session:
        for role_type in RoleType:
            existing = session.execute(
                select(Role).where(Role.name == role_type)
            ).scalar_one_or_none()
            if existing is None:
                session.add(Role(name=role_type))
                print(f"  inserted: {role_type.value}")
            else:
                print(f"  skipped (already exists): {role_type.value}")
        session.commit()

def seed_users() -> None:
    """動作確認用ユーザーを投入する。すでに存在すればスキップ。"""
    test_users: list[SeedUser] = [
        {"username": "sys_admin", "password": "admin", "role": RoleType.SYSTEM_ADMIN},
        {"username": "loc_admin", "password": "admin", "role": RoleType.LOCATION_ADMIN},
        {"username": "loc_operator", "password": "operator", "role": RoleType.LOCATION_OPERATOR},
    ]
    with SessionLocal() as session:
        for u in test_users:
            existing = session.execute(
                select(User).where(User.username == u["username"])
            ).scalar_one_or_none()
            if existing is not None:
                print(f"  skipped (already exists): {u['username']}")
                continue
            role = session.execute(
                select(Role).where(Role.name == u["role"])
            ).scalar_one_or_none()
            if role is None:
                print(f"  skipped (role not found): {u['role']}")
                continue
            user = User(
                username=u["username"],
                hashed_password=auth.hash_password(u["password"]),
                roles=[role],
            )
            session.add(user)
            print(f"  inserted: {u['username']} ({u['role'].value})")
        session.commit()


def main() -> None:
    print("Seeding roles...")
    seed_roles()
    print("Seeding users...")
    seed_users()
    print("Done.")


if __name__ == "__main__":
    main()