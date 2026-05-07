# Chapter 8: API テスト (pytest)

[<- 目次に戻る](../../README.md)

## この章のゴール

- **pytest** でテストを書く基礎を理解する
- テスト用 DB を **セッションスコープで 1 回だけ作成** し、各テストは **SAVEPOINT + ROLLBACK** で高速に隔離する
- **`TestClient`** と **依存性オーバーライド** でエンドポイントをテストする
- **正常系 + 異常系**(422, 400, 401, 403, 404)を含むテストを書く

## スタート地点

```bash
# 前章 (Chapter 7) の完成状態から始めます
git checkout chapter07-end
```

## 完成形

```bash
git checkout chapter08-end
```

---

## はじめに

これまで動作確認は `curl` で手動で行ってきましたが、コードが変更されるたびに手動で全パターンを確認するのは現実的ではありません。

**自動テスト** を書いておけば：
- コード変更のたびに `pytest` 1 コマンドで全パターンを検証できる
- リファクタリングしても「既存の動作が壊れていない」ことを保証できる
- CI (Chapter 15) で PR ごとに自動実行して、壊れたコードがマージされるのを防げる

---

## 1. テスト戦略

### テスト速度と隔離性の両立

テストで一番大事なのは **各テスト関数が互いに独立していること**(テスト A の結果がテスト B に影響しない)です。

ナイーブな方法は「テスト関数ごとに DB を DROP -> CREATE -> マイグレーション -> シードデータ投入」ですが、これは非常に遅くなります。テストが 30 個あれば 30 回 DB を作り直すことになります。

本教材では **SAVEPOINT (ネストされたトランザクション)** パターンを使います：

```
pytest セッション開始:
  -> テスト用 DB 作成 (1 回だけ)
  -> Alembic マイグレーション適用 (1 回だけ)
  -> シードデータ投入 (1 回だけ)

テスト関数 1:
  -> BEGIN (外側のトランザクション)
  -> SAVEPOINT (内側)
  -> テスト実行 (INSERT, UPDATE, DELETE... + endpoint 内の commit は SAVEPOINT の中)
  -> ROLLBACK TO SAVEPOINT (全変更が消える)
  -> ROLLBACK (外側)

テスト関数 2:
  -> (同じ流れ、DB はシードデータだけの状態から始まる)

pytest セッション終了:
  -> テスト用 DB 削除
```

| メリット | 理由 |
|---|---|
| **高速** | DB 作成 + マイグレーション + シードデータは 1 回だけ |
| **完全な隔離** | 各テストは ROLLBACK で元に戻るので互いに干渉しない |
| **実際の DB を使う** | モックではなく本物の PostgreSQL でテストするので、SQL の挙動が本番と一致する |

---

## 2. pytest と関連ライブラリのインストール

```bash
cd $PROJECT_DIR/backend
uv add --dev 'pytest~=9.0.3' 'httpx~=0.28.1'
```

- **`pytest`**: Python のテストフレームワーク
- **`httpx`**: FastAPI の `TestClient` が内部で使う HTTP クライアント

### ディレクトリ構成

```
backend/
├── app/
│   └── ...
└── tests/           <- 新規作成
    ├── __init__.py
    ├── conftest.py  <- fixture (テストの前後処理)
    └── test_api.py  <- テスト本体
```

```bash
mkdir -p $PROJECT_DIR/backend/tests
touch $PROJECT_DIR/backend/tests/__init__.py
touch $PROJECT_DIR/backend/tests/conftest.py
touch $PROJECT_DIR/backend/tests/test_api.py
```

---

## 3. conftest.py: テスト用 fixture の実装

### fixture とは

pytest の **fixture** は「テスト関数の **前後処理** を定義する仕組み」です。

テストでは「**テスト対象の処理を実行する前に、特定の状態を準備したい**」場面が頻繁にあります。例えば：
- テスト用 DB を作る
- テスト用のセッションを開く
- テスト用のユーザーを作成してログインしておく

これらの準備処理を **fixture** として定義し、テスト関数の引数に書くだけで **自動的に実行される** 仕組みです。

```python
import pytest

# fixture を定義
@pytest.fixture()
def greeting():
    """テスト関数に "hello" を渡す fixture"""
    return "hello"


# テスト関数の引数に fixture 名を書くと、自動で実行され結果が渡される
def test_greeting(greeting):
    assert greeting == "hello"
```

#### yield を使った前後処理

`yield` を使うと **テスト実行前の処理** と **テスト実行後のクリーンアップ** を 1 つの fixture にまとめて書けます。

```python
@pytest.fixture()
def db_session():
    session = create_session()     # テスト前: セッション作成
    yield session                  # テスト関数に session を渡す
    session.rollback()             # テスト後: ロールバック (クリーンアップ)
    session.close()
```

- `yield` より上 = **テスト実行前** に走る(セットアップ)
- `yield` で渡す値 = テスト関数が **引数で受け取る値**
- `yield` より下 = **テスト実行後** に走る(クリーンアップ)

#### scope(スコープ)

fixture には **どの単位で実行するか** を `scope` パラメータで指定できます。

| scope | 実行タイミング | 用途 |
|---|---|---|
| `"function"` (デフォルト) | **テスト関数ごと** に毎回実行 | テストごとに独立した状態が必要なもの(セッション、テストデータ) |
| `"class"` | テストクラスごとに 1 回 | クラス内で共有する前提のリソース |
| `"session"` | **pytest 実行全体で 1 回だけ** | DB の作成・削除のように、毎テスト作り直すとコストが高いもの |

#### conftest.py

pytest は **`conftest.py`** という名前のファイルを自動で読み込み、中に定義された fixture を同じディレクトリ以下のテストから使えるようにします。import 不要で使えるのが特徴です。

---

### 実装

`conftest.py` に fixture を定義していきます。

```python
# backend/tests/conftest.py
"""テスト用 fixture。"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from app.config import env
from app.main import app
from app.model import Base, Role, RoleType, User
from app.session import get_session
from app import auth


# テスト用 DB の URL
TEST_DB_NAME = "app_test"
TEST_DB_URL = env.database_url.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"


# scope="session" : pytest セッション全体で1回だけ実行される 
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
    # Alembic ではなく Base.metadata.create_all() を使うのは、 テスト DB はマイグレーション履歴が不要だから (モデル定義から直接テーブルを作る方が高速でシンプル)
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


# scope="function" : 各テスト関数ごとに実行。 SAVEPOINT で囲み、 終了時に ROLLBACK する。
# テスト対象のコードを一切変更せずに隔離できるのがこのパターンの強み
@pytest.fixture()
def db_session():
    """各テスト関数ごと: SAVEPOINT で囲み、終了時に ROLLBACK する。"""
    engine = create_engine(TEST_DB_URL)
    connection = engine.connect()

    # 外側のトランザクションを開始 (BEGIN)
    transaction = connection.begin()

    # join_transaction_mode="create_savepoint" : テスト関数内で実行される session.commit()が COMMIT から SAVEPOINT に差し替わる
    # SAVEPOINT はもともと、トランザクション内にポイントを設定して、一部のみロールバックを可能にするPostgreSQLの機能
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    # 外側のトランザクションを ROLLBACK することで、 BEGIN 以降の全変更 (SAVEPOINT 含む) を巻き戻す
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture()
def client(db_session: Session):
    """FastAPI の TestClient。get_session をテスト用セッションに差し替える。"""
    def _override_get_session():
        yield db_session

    # 依存関係オーバーライドで get_session をテスト用の db_session に差し替える。
    # これにより、 エンドポイント内で Depends(get_session) が呼び出されると、fixtureで定義したdb_sessionが呼び出される
    app.dependency_overrides[get_session] = _override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# 認証が必要なテストで毎回ログインリクエストを書かなくて済むように、 ログインヘルパーを fixture として切り出す
@pytest.fixture()
def admin_token(client: TestClient) -> str:
    """テスト用管理者のログイントークンを取得する。"""
    response = client.post("/api/v1/login", json={"username": "test_admin", "password": "admin_pass"})
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token: str) -> dict:
    """認証ヘッダを返す。"""
    return {"Authorization": f"Bearer {admin_token}"}
```

> [!NOTE] ポイント解説:
> - **`db_session` の SAVEPOINT の仕組み**  
>   `db_session` fixture の処理の流れを DB に発行される SQL と対応付けて見ると仕組みが分かります：
>   ```python
>   engine = create_engine(TEST_DB_URL)
>   connection = engine.connect()
>   transaction = connection.begin()           # -> DB: BEGIN;
>   session = Session(bind=connection, join_transaction_mode="create_savepoint")
>   yield session                              # -> テスト関数にこの session を渡す
>   session.close()
>   transaction.rollback()                     # -> DB: ROLLBACK; (BEGIN 以降の全変更が消える)
>   connection.close()
>   ```
>   
>   テスト実行中、エンドポイント内で `session.commit()` が呼ばれると、DB に発行される SQL は以下のようになります：
>   
>   ```sql
>   BEGIN;                                 -- fixture: connection.begin()
>   SAVEPOINT sa1;                         -- fixture: Session(...)           -> 生成時にSAVEPOINT sa1 を発行
>   INSERT INTO users (...) VALUES (...);  -- エンドポイント: DB操作
>   RELEASE SAVEPOINT sa1;                 -- エンドポイント: session.commit()     -> SAVEPOINT sa1 を解放
>   SAVEPOINT sa2;                         -- エンドポイント: session.commit()     -> 新しい SAVEPOINT sa2 を発行
>   UPDATE items SET ... WHERE ...;        -- エンドポイント: DB操作
>   RELEASE SAVEPOINT sa2;                 -- エンドポイント: session.commit()     -> SAVEPOINT sa2 を解放
>   ROLLBACK;                              -- fixture: transaction.rollback() -> BEGIN 以降の全 SQL (SAVEPOINT 含む) が巻き戻る
>   ```

> [!TIP] 公式ドキュメント
> - [依存関係のオーバーライド | FastAPI](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
> - [fixture について | Pytest](https://docs.pytest.org/en/stable/explanation/fixtures.html)

---

## 4. テストを書く

`backend/tests/test_api.py` にテストを実装します。

```python
# backend/tests/test_api.py
"""API のテスト。"""
from fastapi.testclient import TestClient


class TestLogin:
    """ログイン API のテスト。"""

    def test_login_success(self, client: TestClient):
        """正しい認証情報でログインできる"""
        response = client.post("/api/v1/login", json={"username": "test_admin", "password": "admin_pass"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient):
        """パスワードが間違っている場合は 401"""
        response = client.post("/api/v1/login", json={"username": "test_admin", "password": "wrong"})
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """存在しないユーザーでログインすると 401"""
        response = client.post("/api/v1/login", json={"username": "nobody", "password": "pass"})
        assert response.status_code == 401


class TestUserCRUD:
    """ユーザー CRUD のテスト。"""

    def test_create_user(self, client: TestClient, auth_headers: dict):
        """ユーザーを作成できる"""
        response = client.post(
            "/api/v1/users/",
            json={"username": "newuser", "password": "secret", "role_ids": [1]},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert "id" in data
        assert "hashed_password" not in data  # パスワードはレスポンスに含まれない

    def test_create_user_duplicate(self, client: TestClient, auth_headers: dict):
        """既に存在するユーザー名で作成すると 400"""
        client.post(
            "/api/v1/users/",
            json={"username": "duplicate", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        response = client.post(
            "/api/v1/users/",
            json={"username": "duplicate", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    def test_create_user_invalid_role(self, client: TestClient, auth_headers: dict):
        """存在しない role_id を指定すると 400"""
        response = client.post(
            "/api/v1/users/",
            json={"username": "user2", "password": "pass", "role_ids": [999]},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_create_user_validation_error(self, client: TestClient, auth_headers: dict):
        """必須フィールドが欠けると 422"""
        response = client.post(
            "/api/v1/users/",
            json={"password": "pass", "role_ids": [1]},  # username が無い
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_get_user(self, client: TestClient, auth_headers: dict):
        """ユーザーを取得できる"""
        # まず作成
        create_res = client.post(
            "/api/v1/users/",
            json={"username": "getme", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        user_id = create_res.json()["id"]

        # 取得
        response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["username"] == "getme"

    def test_get_user_not_found(self, client: TestClient, auth_headers: dict):
        """存在しないユーザー ID で取得すると 404"""
        response = client.get("/api/v1/users/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_list_users(self, client: TestClient, auth_headers: dict):
        """ユーザー一覧を取得できる"""
        response = client.get("/api/v1/users/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # 少なくとも test_admin がいる

    def test_update_user(self, client: TestClient, auth_headers: dict):
        """ユーザーを部分更新できる"""
        create_res = client.post(
            "/api/v1/users/",
            json={"username": "updateme", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        user_id = create_res.json()["id"]

        response = client.patch(
            f"/api/v1/users/{user_id}",
            json={"avatar_url": "https://example.com/new.png"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["avatar_url"] == "https://example.com/new.png"

    def test_delete_user(self, client: TestClient, auth_headers: dict):
        """ユーザーを削除できる"""
        create_res = client.post(
            "/api/v1/users/",
            json={"username": "deleteme", "password": "pass", "role_ids": [1]},
            headers=auth_headers,
        )
        user_id = create_res.json()["id"]

        response = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == 204

        # 削除後に取得すると 404
        response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == 404


class TestAuthentication:
    """認証が必要なエンドポイントのテスト。"""

    def test_unauthenticated_access(self, client: TestClient):
        """認証なしでアクセスすると 401"""
        response = client.get("/api/v1/users/")
        assert response.status_code == 401

    def test_invalid_token(self, client: TestClient):
        """無効なトークンで 401"""
        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestAuthorization:
    """認可(ロールベース)のテスト。"""

    def test_operator_cannot_create_user(self, client: TestClient, auth_headers: dict):
        """LOCATION_OPERATOR は USER_CREATE 権限がないので 403"""
        # OPERATOR ユーザーを作成
        client.post(
            "/api/v1/users/",
            json={"username": "operator", "password": "pass", "role_ids": [3]},
            headers=auth_headers,
        )
        # OPERATOR でログイン
        login_res = client.post("/api/v1/login", json={"username": "operator", "password": "pass"})
        operator_token = login_res.json()["access_token"]
        operator_headers = {"Authorization": f"Bearer {operator_token}"}

        # ユーザー作成を試みる -> 403
        response = client.post(
            "/api/v1/users/",
            json={"username": "forbidden", "password": "pass", "role_ids": [3]},
            headers=operator_headers,
        )
        assert response.status_code == 403


class TestItemCRUD:
    """アイテム CRUD のテスト。"""

    def test_create_and_list_items(self, client: TestClient, auth_headers: dict):
        """アイテムを作成して一覧に含まれることを確認"""
        # 作成
        response = client.post(
            "/api/v1/items/",
            json={"title": "Test Item", "content": "Hello"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        item = response.json()
        assert item["title"] == "Test Item"

        # 一覧
        response = client.get("/api/v1/items/", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()
        assert any(i["title"] == "Test Item" for i in items)

    def test_item_ownership(self, client: TestClient, auth_headers: dict):
        """他のユーザーのアイテムにはアクセスできない (403)"""
        # admin でアイテム作成
        create_res = client.post(
            "/api/v1/items/",
            json={"title": "Admin Item", "content": "Secret"},
            headers=auth_headers,
        )
        item_id = create_res.json()["id"]

        # 別ユーザー (OPERATOR) を作成・ログイン
        client.post(
            "/api/v1/users/",
            json={"username": "other_user", "password": "pass", "role_ids": [3]},
            headers=auth_headers,
        )
        login_res = client.post("/api/v1/login", json={"username": "other_user", "password": "pass"})
        other_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # 他人のアイテムを取得 -> 403
        response = client.get(f"/api/v1/items/{item_id}", headers=other_headers)
        assert response.status_code == 403
```

### テスト設計のポイント

| パターン | テストすべき内容 |
|---|---|
| **正常系** | 期待通りのステータスコードとレスポンスボディが返る |
| **バリデーションエラー (422)** | 必須フィールド欠損、型違い |
| **ビジネスロジックエラー (400)** | 重複ユーザー名、存在しない role_id |
| **認証エラー (401)** | トークンなし、無効なトークン |
| **認可エラー (403)** | 権限不足、他人のリソースへのアクセス |
| **リソース不存在 (404)** | 存在しない ID でアクセス |
| **副作用の確認** | 作成後に取得できる、削除後に取得すると 404 |

> [!NOTE] テスト関数名は「何をテストしているか」が読み取れるように
> `test_create_user_duplicate`, `test_operator_cannot_create_user` のように、「**条件 + 期待する結果**」を名前に含めると、テストが失敗したときに何が壊れたのか一目で分かります。

---

## 5. テストの実行

```bash
cd $PROJECT_DIR/backend

# 環境変数を export (テスト DB 作成に必要)
export $(grep -v '^#' $PROJECT_DIR/backend/.env | xargs)

# テスト実行
uv run pytest tests/ -v
```

`-v` (verbose) を付けると、各テスト関数の実行結果が 1 行ずつ表示されます。

### 出力例

```
tests/test_api.py::TestLogin::test_login_success PASSED                        [  5%]
tests/test_api.py::TestLogin::test_login_wrong_password PASSED                 [ 11%]
tests/test_api.py::TestLogin::test_login_nonexistent_user PASSED               [ 17%]
tests/test_api.py::TestUserCRUD::test_create_user PASSED                       [ 23%]
tests/test_api.py::TestUserCRUD::test_create_user_duplicate PASSED             [ 29%]
tests/test_api.py::TestUserCRUD::test_create_user_invalid_role PASSED          [ 35%]
tests/test_api.py::TestUserCRUD::test_create_user_validation_error PASSED      [ 41%]
tests/test_api.py::TestUserCRUD::test_get_user PASSED                          [ 47%]
tests/test_api.py::TestUserCRUD::test_get_user_not_found PASSED                [ 52%]
tests/test_api.py::TestUserCRUD::test_list_users PASSED                        [ 58%]
tests/test_api.py::TestUserCRUD::test_update_user PASSED                       [ 64%]
tests/test_api.py::TestUserCRUD::test_delete_user PASSED                       [ 70%]
tests/test_api.py::TestAuthentication::test_unauthenticated_access PASSED      [ 76%]
tests/test_api.py::TestAuthentication::test_invalid_token PASSED               [ 82%]
tests/test_api.py::TestAuthorization::test_operator_cannot_create_user PASSED  [ 88%]
tests/test_api.py::TestItemCRUD::test_create_and_list_items PASSED             [ 94%]
tests/test_api.py::TestItemCRUD::test_item_ownership PASSED                    [100%]

================================= 17 passed in 1.44s =================================
```

全テストが通れば成功です。**2〜3 秒** で 17 個のテストが実行されます(DB 作成は 1 回だけ、各テストは ROLLBACK で高速)。

### テストが失敗したら

```
FAILED tests/test_api.py::TestUserCRUD::test_create_user - AssertionError: assert 500 == 201
```

のような出力になります。ステータスコードが期待と異なる場合は `response.json()` の中身を `print()` して原因を確認しましょう。

---

## 6. pytest の便利なオプション

```bash
# 特定のテストクラスだけ実行
uv run pytest tests/test_api.py::TestLogin -v

# 特定のテスト関数だけ実行
uv run pytest tests/test_api.py::TestUserCRUD::test_create_user -v

# 最初に失敗したテストで止める
uv run pytest tests/ -x

# print() の出力を表示する
uv run pytest tests/ -s

# 前回失敗したテストだけ再実行
uv run pytest tests/ --lf
```

---

## まとめ

この章では以下を学びました：

- **テスト戦略**: セッションスコープで DB を 1 回作成、各テストは SAVEPOINT + ROLLBACK で高速隔離
- **`join_transaction_mode="create_savepoint"`**: テスト対象コードの `commit()` を SAVEPOINT の中に閉じ込め、rollback で巻き戻す
- **`app.dependency_overrides`**: FastAPI の DI をテスト用に差し替える
- **`TestClient`**: FastAPI のエンドポイントに対して HTTP リクエストを投げるテストクライアント
- **テスト設計**: 正常系 + 異常系(422 / 400 / 401 / 403 / 404)を網羅する

これで第 1 部(バックエンド基礎)は完了です。次は第 2 部(フロントエンド)に入ります。

---

## 次の章

[Chapter 9: JS/TS おさらい (外部リンク集) ->](../chapter09/README.md)
