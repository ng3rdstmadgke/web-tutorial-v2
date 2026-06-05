import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app import auth
from app.config import env
from app.main import app
from app.model import Base, Role, RoleType, User
from app.session import get_session

# テスト用 DB の URL
TEST_DB_NAME = "app_test"
TEST_DB_URL = env.database_url.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """pytest セッション全体で 1 回だけ実行: テスト DB を作成しスキーマを適用する。"""
    # デフォルト DB に接続してテスト DB を作成
    default_engine = create_engine(env.database_url, isolation_level="AUTOCOMMIT")
    with default_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    default_engine.dispose()

    # テスト DB にスキーマを作成
    test_engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(test_engine)

    # トリガー関数とトリガーを作成
    with test_engine.begin() as conn:
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
              NEW.updated = CURRENT_TIMESTAMP;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        for table_name in ("users", "items", "roles", "user_roles"):
            conn.execute(text(f"""
                CREATE OR REPLACE TRIGGER set_{table_name}_updated_at
                BEFORE UPDATE ON {table_name}
                FOR EACH ROW
                EXECUTE FUNCTION set_updated_at();
            """))

    # シードデータを投入
    TestSessionLocal = sessionmaker(bind=test_engine)
    with TestSessionLocal() as session:
        for role_type in RoleType:
            session.add(Role(name=role_type))
        session.commit()

        # テスト用管理者ユーザー
        admin_role = session.query(Role).filter(Role.name == RoleType.SYSTEM_ADMIN).first()
        admin_user = User(
            username="test_admin",
            hashed_password=auth.hash_password("admin_pass"),
            roles=[admin_role],
        )
        session.add(admin_user)
        session.commit()

    test_engine.dispose()

    yield

    # クリーンアップ: テスト DB を削除
    with default_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    default_engine.dispose()


@pytest.fixture()
def db_session():
    """各テスト関数ごと: SAVEPOINT で囲み、終了時に ROLLBACK する。"""
    engine = create_engine(TEST_DB_URL)
    connection = engine.connect()

    # 外側のトランザクションを開始
    transaction = connection.begin()

    # セッションを作成 (このセッション内の commit は SAVEPOINT に対して行われる)
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    # テスト終了 → 全変更を取り消す
    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture()
def client(db_session: Session):
    """FastAPI の TestClient。get_session をテスト用セッションに差し替える。"""
    def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    """テスト用管理者のログイントークンを取得する。"""
    response = client.post("/api/v1/login", json={"username": "test_admin", "password": "admin_pass"})
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token: str) -> dict:
    """認証ヘッダを返す。"""
    return {"Authorization": f"Bearer {admin_token}"}