"""シードデータ（初期データ）を投入するスクリプト。

冪等に書くことで、何度実行してもエラーにならず、最終的に同じ状態になる。

実行方法:
    cd $PROJECT_DIR/backend
    uv run python -m app.seed
"""
from sqlalchemy import select

from app.model import Role, RoleType
from app.session import SessionLocal


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


def main() -> None:
    print("Seeding roles...")
    seed_roles()
    print("Done.")


if __name__ == "__main__":
    main()