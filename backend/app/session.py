from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import env


engine = create_engine(env.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)


def get_session() -> Generator[Session, None, None]:
    """1 リクエスト 1 セッションで使うジェネレータ。
    後の章で FastAPI の `Depends` と組み合わせて使う。
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
