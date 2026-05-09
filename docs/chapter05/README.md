# Chapter 5: CRUD API の実装

[← 目次に戻る](../README.md)

## この章のゴール

- **Pydantic** でリクエスト/レスポンスのスキーマを型付きで定義する
- ユーザーの **作成・取得・一覧・更新・削除** API を `FastAPI` で実装する
- **`Depends(get_session)`** で DB セッションを依存性注入する
- **`pwdlib`** でパスワードを Argon2 でハッシュ化する
- **`APIRouter`** でルートをモジュールに分離し、`prefix="/api/v1"` を付ける

## スタート地点

```bash
git checkout chapter05-start
```

## 完成形

```bash
git checkout chapter05-end
```

---

## はじめに

Chapter 4 までで、PostgreSQL + SQLAlchemy + Alembic の基盤が整いました。`backend/app/` には：

- **`config.py`** … 環境変数を読み込む設定オブジェクト
- **`session.py`** … Engine と SessionLocal、`get_session()` 依存
- **`model.py`** … SQLAlchemy のモデル定義
- **`seed.py`** … シードデータ投入スクリプト
- **`main.py`** … Hello World が返るだけの FastAPI アプリ

がある状態です。この章では `main.py` に「ユーザーの CRUD API」を実装していきます。

> **この章で扱わないこと**  
> ログイン・認証・JWT トークン発行は **次の Chapter 6** で扱います。Chapter 5 終了時点では「**誰でもユーザーを CRUD できる**」状態になりますが、本格的な認証は Chapter 6 で被せていきます。
>
> Item の CRUD も Chapter 6 で **「認証されたユーザーが自分の Item を管理する」** という流れで実装するため、本章では User の CRUD だけに絞ります。

---

## 1. compose.yaml を整える（.env の読み込みと自動マイグレーション）

この章から、アプリがDBに接続する必要があるので、`backend` コンテナにDBの接続情報を含む環境変数ファイルを渡し、起動時にマイグレーション実行する `migrate` サービスを `compose.yaml` に追加します。`backend` はこの `migrate` の完了を待ってから起動するようにします。


```yaml
# compose.yaml
services:
  backend:
    container_name: web-tutorial-v2-backend-${HOST_USER}
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    env_file:                        # ← 追加: .env をコンテナに渡す
      - backend/.env
    ports:
      - "8000:8000"
    volumes:
      - ${HOST_DIR}/backend/app:/opt/backend/app
    depends_on:                      # ← 追加: migrate 完了後に起動する
      migrate:
        condition: service_completed_successfully  # ←
    networks:
      - devcontainer-nw

  migrate:                           # ← 追加: マイグレーション + シードのワンショット実行
    container_name: web-tutorial-v2-migrate-${HOST_USER}
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    env_file:
      - backend/.env
    volumes:
      # app に加えて alembic 一式もマウントする (マイグレーションの適用に必要)
      - ${HOST_DIR}/backend/app:/opt/backend/app
      - ${HOST_DIR}/backend/alembic:/opt/backend/alembic
      - ${HOST_DIR}/backend/alembic.ini:/opt/backend/alembic.ini
    command: ["sh", "-c", "uv run alembic upgrade head && uv run python -m app.seed"]
    depends_on:
      db:
        condition: service_healthy   # db が受付可能になってから実行する
    restart: "no"                    # 一度きり実行して終了する (再起動しない)
    networks:
      - devcontainer-nw

  db:
    container_name: web-tutorial-v2-db-${HOST_USER}
    image: postgres:18-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app_pass
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    healthcheck:                     # ← 追加: 起動完了を待てるようにする
      test: ["CMD-SHELL", "pg_isready -U app -d app"]  # ←
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - devcontainer-nw

networks:
  devcontainer-nw:
    external: true
    name: br-web-tutorial-v2-${HOST_USER}
```

> [!NOTE] ポイント解説:
> - **`depends_on` の `condition` で起動順を制御**  
>   [Control startup order](https://docs.docker.com/compose/how-tos/startup-order/)  
>   1. `db` の `healthcheck`（`pg_isready` で接続を確認）が通る
>   2. `migrate` がマイグレーション + シードを実行して**正常終了**する（`service_completed_successfully`）
>   3. `backend` が起動

---

## 2. アプリの起動

`migrate` サービスのおかげで、起動はコマンド 1 つで済みます。`docker compose up` すると、`db` -> `migrate`（マイグレーション + シード）-> `backend` の順に立ち上がります。

```bash
cd $PROJECT_DIR

# db -> migrate(マイグレーション+シード) -> backend の順で起動する
docker compose down && docker compose up -d --build

# コンテナのログを tail したい場合はこちら
docker compose logs -f
```

---

## 3. REST API と HTTP メソッド

CRUD API を実装する前に、「**REST API**」の基本的な設計ルールを整理しておきます。

### REST API とは

**REST (Representational State Transfer)** は、Web API を設計する際に広く使われている設計スタイルです。REST では：

- **URL（エンドポイント）はリソース（データ）を表す**（例: `/api/v1/users/1` = 「ID=1 のユーザーというリソース」）
- **HTTP メソッドでそのリソースに対する操作を表す**（例: `GET /api/v1/users/1` = 「ID=1 のユーザーを取得する」）

つまり **「何を」が URL**、**「どうする」が HTTP メソッド** という分離になっています。

### HTTP メソッドと CRUD の対応

| HTTP メソッド | 意味 | CRUD 操作 | URL の例 | リクエストボディ |
|---|---|---|---|---|
| **POST** | 新しいリソースを作成する | Create | `POST /api/v1/users/` | あり（作成データ） |
| **GET** | リソースを取得する | Read | `GET /api/v1/users/1` | なし |
| **PUT** | リソースを**全体**置き換える | Full Update | `PUT /api/v1/users/1` | あり（全フィールド必須） |
| **PATCH** | リソースを**部分的に**更新する | Partial Update | `PATCH /api/v1/users/1` | あり（変更フィールドだけ） |
| **DELETE** | リソースを削除する | Delete | `DELETE /api/v1/users/1` | なし |

> **PUT vs PATCH**  
> どちらも「更新」に使いますが、意味が異なります：
> - **PUT**: 「このリソースをまるごとこの内容に差し替えてください」。送らなかったフィールドはデフォルトに戻る
> - **PATCH**: 「このリソースのここだけ変えてください」。送ったフィールドだけが変わり、他はそのまま
>
> 本教材では、更新 API は「指定されたフィールドだけ更新する」部分更新なので **PATCH** を使います。

### HTTP ステータスコード

API がレスポンスとして返す **3 桁の数字** です。ステータスコードは**百の位でカテゴリ**が決まっています。

#### カテゴリ

| カテゴリ | 意味 | 概要 |
|---|---|---|
| **1xx** | Informational | 処理が進行中（通常の API 開発ではほぼ使わない） |
| **2xx** | Success | リクエストが**正常に処理**された |
| **3xx** | Redirection | 別の URL に転送する（Chapter 2 で 302 を使った） |
| **4xx** | Client Error | **クライアント側の問題**（リクエストが不正、認証切れ、リソースが無いなど） |
| **5xx** | Server Error | **サーバー側の問題**（バグ、DB 接続不能、タイムアウトなど） |

#### 2xx: 成功系（よく使うもの）

| コード | 名前 | 用途 |
|---|---|---|
| **200** | OK | 汎用の成功レスポンス。GET で取得成功、PATCH で更新成功など |
| **201** | Created | **リソースの新規作成に成功**。POST で使う。レスポンスボディに作成されたリソースを含めるのが一般的 |
| **204** | No Content | 成功したが**返すボディが無い**。DELETE で削除成功時に使う |

#### 3xx: リダイレクト系

| コード | 名前 | 用途 |
|---|---|---|
| **301** | Moved Permanently | リソースが恒久的に別の URL に移動した |
| **302** | Found | 一時的に別の URL に転送する（Chapter 2 の PRG パターンで使用） |
| **304** | Not Modified | キャッシュが有効。ボディを返さず、クライアント側のキャッシュを使わせる |

#### 4xx: クライアントエラー（よく使うもの）

| コード | 名前 | 用途 |
|---|---|---|
| **400** | Bad Request | リクエストの内容が不正（バリデーション以前の問題、存在しない role_id を指定したなど） |
| **401** | Unauthorized | **認証されていない**（トークンが無い、期限切れ）。Chapter 6 で使う |
| **403** | Forbidden | **認可されていない**（認証済みだが権限が無い）。Chapter 6 で使う |
| **404** | Not Found | リクエストした URL のリソースが存在しない |
| **409** | Conflict | リソースの状態と矛盾する操作（ユーザー名の重複など。本教材では 400 で代用） |
| **422** | Unprocessable Entity | リクエストの**構文は正しいがバリデーションに失敗**した。FastAPI が Pydantic バリデーションエラー時に自動で返す |

#### 5xx: サーバーエラー

| コード | 名前 | 用途 |
|---|---|---|
| **500** | Internal Server Error | サーバー内部で予期しないエラーが発生。コードのバグや DB 接続不能など |
| **502** | Bad Gateway | リバースプロキシが背後のサーバーから不正なレスポンスを受けた |
| **503** | Service Unavailable | サーバーが一時的に利用不可（メンテナンス中、過負荷） |
| **504** | Gateway Timeout | リバースプロキシが背後のサーバーからの応答を待ちきれなかった |

> **覚え方のコツ**  
> - **2xx = 成功**（クライアントもサーバーも問題なし）
> - **4xx = クライアントが悪い**（リクエストを直すのはクライアントの責任）
> - **5xx = サーバーが悪い**（サーバー側のバグや障害を直す必要がある）
>
> API 設計では「**4xx を返すべき場面で 5xx を返してしまう**」と、運用時に「サーバーのバグなのかクライアントの誤りなのか」の切り分けが困難になります。ステータスコードを正しく使い分けることは運用品質に直結します。

### 本章で使うステータスコード

| 操作 | 成功時のステータス | エラー時のステータス |
|---|---|---|
| ユーザー作成 (POST) | 201 Created | 400 Bad Request / 422 |
| ユーザー取得 (GET) | 200 OK | 404 Not Found |
| ユーザー一覧 (GET) | 200 OK | — |
| ユーザー更新 (PATCH) | 200 OK | 400 / 404 |
| ユーザー削除 (DELETE) | 204 No Content | 404 Not Found |

---

## 4. なぜ Pydantic が必要なのか

FastAPI では **リクエストボディとレスポンスを `pydantic` のモデルで定義する** のが定石です。なぜそうするのかを実例で確認します。

### Pydantic を使わない場合

```python
def create_user(session, data):
    # data から取り出す値の型はぱっと見では分からない
    user = User(
        username=data["username"],
        hashed_password=hash(data["password"]),
        avatar_url=data.get("avatar_url"),
        roles=...,
    )
    session.add(user)
    session.commit()
    return {
        "id": user.id,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "roles": [{"id": r.id, "name": r.name} for r in user.roles],
    }
```

問題点：

- `data` が何を持つ辞書なのか **型から読み取れない**
- レスポンスとして返す辞書の構造も **読み取りにくい**
- フィールドの欠損や型違反が **実行時まで気づかない**
- API ドキュメントを別途整備する必要がある

### Pydantic を使う場合

```python
class UserCreate(BaseModel):
    username: str
    password: str
    avatar_url: str | None = None
    role_ids: list[int]


class UserRead(BaseModel):
    id: int
    username: str
    avatar_url: str | None
    roles: list[RoleRead]


def create_user(session: Session, data: UserCreate) -> UserRead:
    user = User(
        username=data.username,
        hashed_password=hash(data.password),
        avatar_url=data.avatar_url,
        roles=...,
    )
    session.add(user)
    session.commit()
    return UserRead.model_validate(user)
```

メリット：

- **シグネチャから受け取る型・返す型が明確**
- フィールド欠損や型違反は FastAPI が自動で **`422 Unprocessable Entity`** を返す
- **OpenAPI（Swagger UI）が自動生成** される

> **Pydantic とは何か（おさらい）**  
> Chapter 2 で軽く触れた通り、`pydantic` は「**型ヒントから自動的にバリデーションと JSON シリアライズを行う**」ライブラリです。`BaseModel` を継承したクラスを作れば、`User.model_validate(dict)` で辞書 → オブジェクト、`user.model_dump()` でオブジェクト → 辞書、`user.model_dump_json()` で JSON 化、が型安全にできます。

---

## 5. パスワードハッシュ化ユーティリティ

ユーザー作成時に **パスワードをそのまま DB に保存するのは絶対 NG** です。万が一 DB が漏洩したときに、すべてのユーザーのパスワードがそのまま流出してしまいます。

代わりに **不可逆なハッシュ値** に変換して保存します。ハッシュアルゴリズムには **Argon2** を使います（現在の OWASP 推奨）。

### pwdlib をインストール

FastAPI 公式チュートリアルが推奨する [`pwdlib`](https://github.com/frankie567/pwdlib) を採用します。`pwdlib` は複数のハッシュアルゴリズムを統一インターフェースで扱える Python ライブラリで、`PasswordHash.recommended()` を呼ぶと **Argon2 を推奨設定** で使うインスタンスが取得できます。

```bash
cd $PROJECT_DIR/backend
uv add 'pwdlib[argon2]~=0.3.0'
```

> **Argon2 とは**  
> 2015 年の Password Hashing Competition で優勝したアルゴリズム。**メモリハードな関数**で GPU/ASIC 攻撃に強く、現代のパスワード保存の業界標準です。長年使われてきた **bcrypt** も依然として安全な選択肢ですが、新規プロジェクトでは Argon2 が推奨されています。

### auth.py を作成

```bash
touch $PROJECT_DIR/backend/app/auth.py
```

```python
# backend/app/auth.py
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
```

### 動作確認

```bash
cd $PROJECT_DIR/backend
uv run python -c "
from app.auth import hash_password, verify_password
h = hash_password('mypassword')
print('hash:', h)
print('verify (correct):', verify_password('mypassword', h))
print('verify (wrong):', verify_password('wrong', h))
"
# hash: $argon2id$v=19$m=65536,t=3,p=4$...
# verify (correct): True
# verify (wrong): False
```

`hash_password` を同じ平文に対して何度実行しても **毎回違うハッシュが返ります**（先頭の `$argon2id$...` 部分にソルトが含まれている）。これが正しい挙動です。

---

## 6. Pydantic スキーマを定義する

`backend/app/schemas.py` を作って、リクエスト・レスポンスのスキーマを定義します。

```bash
touch $PROJECT_DIR/backend/app/schemas.py
```

### 命名規則

FastAPI / SQLModel コミュニティでは、以下の命名規則が広く使われています：

| サフィックス | 用途 |
|---|---|
| `Base` | 共通フィールド（継承元） |
| `Create` | POST 時の入力 (リクエストボディ) |
| `Update` | PATCH 時の入力（部分更新） |
| `Read` | レスポンスで返す型 |

これに沿ってスキーマを書きます。

```python
# backend/app/schemas.py
from pydantic import BaseModel, ConfigDict

from app.model import RoleType


# ===== Role =====

class RoleRead(BaseModel):
    """レスポンスで返す Role"""
    id: int
    name: RoleType

    # SQLAlchemy のモデル (= ORM オブジェクト) からも model_validate(...) できるようにする
    model_config = ConfigDict(from_attributes=True)


# ===== User =====

# username / avatar_url は Create / Read で共通なので、 ベースクラスにまとめて DRY 原則に従う
class UserBase(BaseModel):
    """User の共通フィールド (Create / Read で共有)"""
    username: str
    avatar_url: str | None = None


# password は UserCreate のみに置く (平文パスワードはレスポンスに含めない)
class UserCreate(UserBase):
    """POST /api/v1/users/ のリクエストボディ"""
    password: str
    role_ids: list[int]


# 全フィールドが Optional: 部分更新 (クライアントが password だけ変えたい等) に対応する
class UserUpdate(BaseModel):
    """PATCH /api/v1/users/{user_id} のリクエストボディ"""
    password: str | None = None
    avatar_url: str | None = None
    role_ids: list[int] | None = None


class UserRead(UserBase):
    """GET レスポンスとして返す User"""
    id: int
    roles: list[RoleRead]

    # from_attributes=True で SQLAlchemy のモデルから直接 Pydantic モデルに変換できるようにする
    # UserRead.model_validate(user_orm_instance) のような使い方
    model_config = ConfigDict(from_attributes=True)
```

---

## 7. ルーターを別ファイルに分ける

エンドポイントの実装を `main.py` に直接書くと、章を進めるごとに `main.py` が肥大化します。FastAPI には **`APIRouter`** という仕組みがあり、ルートをモジュール単位に分けられます。

```bash
touch $PROJECT_DIR/backend/app/routers.py
```

```python
# backend/app/routers.py
from fastapi import APIRouter

router = APIRouter()

# ここに各エンドポイントを追加していく (次のセクション以降)
```

### main.py に登録

`backend/app/main.py` を以下のように書き換えます：

```python
# backend/app/main.py
from fastapi import FastAPI

from app.routers import router

app = FastAPI()

# /api/v1 プレフィックスでルーターを登録。
# こうしておくことで、APIのインターフェースを変更したい場合に破壊的変更を行わず v2(`/api/v2/...`) を用意する運用ができる
app.include_router(router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Hello World"}

# NOTE: Chapter2で書いた古いエンドポイントは不要なので削除
```

---

## 8. ユーザー作成 API（Create）

`POST /api/v1/users/` でユーザーを作成する API を実装します。

`backend/app/routers.py` を以下のように書き換え：

```python
# backend/app/routers.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth
from app.model import Role, User
from app.schemas import UserCreate, UserRead
from app.session import get_session

router = APIRouter()


@router.post(
    "/users/",
    response_model=UserRead,
    # 作成時は 201 (REST の慣習)。 デフォルトは 200
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    data: UserCreate,
    # Depends(get_session): FastAPI の依存性注入。
    # リクエストのたびに get_session() が呼ばれて セッションが渡され、 レスポンス返却後に自動でクローズされる。
    # I/Oと密結合するインスタンスは関数の外でnewして引数で渡すのがベストプラクティス。(動作確認やテストがしやすくなる)
    session: Session = Depends(get_session),
) -> User:
    # ユーザー名の重複チェック (Chapter 3 で学んだ SQLAlchemy 2.x の SELECT 構文)
    # session.execute(...): クエリの実行。実行結果を返す。
    existing = session.execute(
        # select(User).where(...): クエリの組み立て
        select(User).where(User.username == data.username)
    # .scalar_one_or_none(): 実行結果から単一の値を取得 (無ければ None, 2件以上で例外)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{data.username}' is already taken",
        )

    # role_ids から Role を取得 (存在しない id があれば 404)
    roles: list[Role] = []
    for role_id in data.role_ids:
        role = session.execute(
            select(Role).where(Role.id == role_id)
        ).scalar_one_or_none()
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role not found (id={role_id})",
            )
        roles.append(role)

    user = User(
        username=data.username,
        hashed_password=auth.hash_password(data.password),
        avatar_url=data.avatar_url,
        roles=roles,
    )
    session.add(user)
    session.commit()
    # commit 後に user を DB から再読み込み。
    # id, created, updated など、DB側で自動的に決まる値がモデルインスタンスに反映される
    session.refresh(user)
    # response_model=UserRead により、 SQLAlchemy のモデルを return しても FastAPI が UserRead に変換して返す
    return user
```

### 動作確認

```bash
curl -s -X POST "http://backend:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "yamada",
    "password": "secret",
    "avatar_url": "https://example.com/avatar.png",
    "role_ids": [1, 2]
  }' | jq .
# {
#   "id": 1,
#   "username": "yamada",
#   "avatar_url": "https://example.com/avatar.png",
#   "roles": [
#     {"id": 1, "name": "SYSTEM_ADMIN"},
#     {"id": 2, "name": "LOCATION_ADMIN"}
#   ]
# }
```

`hashed_password` は **レスポンスに含まれない** ことを確認してください（`UserRead` に定義していないため）。

#### バリデーションエラーを試す

```bash
# username を省略してみる
curl -s -X POST "http://backend:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{"password": "secret", "role_ids": [1]}' | jq .
# 422 Unprocessable Entity が返り、どのフィールドが何の理由で不正かが JSON で説明される
# {
#   "detail": [
#     {
#       "type": "missing",
#       "loc": ["body", "username"],
#       "msg": "Field required",
#       "input": {"password": "secret", "role_ids": [1]}
#     }
#   ]
# }
```

---

## 9. ユーザー取得 API（Read 単体）

`GET /api/v1/users/{user_id}` で、ID 指定でユーザー 1 件を取得する API を実装します。

`backend/app/routers.py` の末尾に追加：

```python
# backend/app/routers.py

# ... 既存のコード ...

@router.get("/users/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    session: Session = Depends(get_session),
) -> User:
    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found (id={user_id})",
        )
    return user
```

シンプルですね。`user_id: int` のパスパラメータは Chapter 2 で扱った通り、FastAPI が型変換してくれます。

### 動作確認

```bash
curl -s "http://backend:8000/api/v1/users/1" | jq .
# {"id": 1, "username": "yamada", "avatar_url": "https://example.com/avatar.png", "roles": [...]}
```

存在しない ID なら 404：

```bash
curl -s "http://backend:8000/api/v1/users/99999" | jq .
# {"detail": "User not found (id=99999)"}
```

---

## 10. ユーザー一覧 API（Read 複数）

`GET /api/v1/users/` で、ユーザーの一覧を取得します。**ページング** のためにクエリパラメータ `skip` と `limit` を受け取れるようにします。

```python
# backend/app/routers.py

# ... 既存のコード ...

# response_model=list[UserRead]: 一覧レスポンスは UserRead のリスト
@router.get("/users/", response_model=list[UserRead])
def read_users(
    # クエリパラメータとして受け取り、 デフォルト値あり
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[User]:
    users = session.execute(
        select(User).offset(skip).limit(limit).order_by(User.id)
    # .scalars().all(): ヒットしたレコードを全件取得
    ).scalars().all()
    return list(users)
```

### 動作確認

```bash
curl -s "http://backend:8000/api/v1/users/" | jq .
# [{"id": 1, "username": "yamada", ...}]

# skip / limit でページング
curl -s "http://backend:8000/api/v1/users/?skip=0&limit=10" | jq .
```

---

## 11. ユーザー更新 API（Update）

`PATCH /api/v1/users/{user_id}` で、既存ユーザーを **部分的に更新** する API を実装します。

```python
# backend/app/routers.py

# ... 既存のコード ...

@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: "UserUpdate",
    session: Session = Depends(get_session),
) -> User:
    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found (id={user_id})",
        )

    # UserUpdate のフィールドはすべて Optional なので、 指定されたフィールドだけを更新する
    if data.password is not None:
        user.hashed_password = auth.hash_password(data.password)
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    if data.role_ids is not None:
        roles: list[Role] = []
        for role_id in data.role_ids:
            role = session.execute(
                select(Role).where(Role.id == role_id)
            ).scalar_one_or_none()
            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role not found (id={role_id})",
                )
            roles.append(role)
        # 多対多リレーションを丸ごと差し替え。 SQLAlchemy が中間テーブル user_roles の差分を計算して自動で INSERT / DELETE してくれる
        user.roles = roles

    session.add(user)
    session.commit()
    session.refresh(user)
    return user
```

`UserUpdate` の import を冒頭に追加：

```python
from app.schemas import UserCreate, UserRead, UserUpdate  # ← UserUpdate を追加
```

> **PUT と PATCH の使い分け**  
> HTTP の仕様上：
> - **`PUT`** … リソースを **完全に置き換える**。送られなかったフィールドはデフォルトに戻る
> - **`PATCH`** … リソースを **部分的に更新する**。送られたフィールドだけが変わる
>
> 今回の実装は「Optional なフィールドだけ更新する部分更新」なので、HTTP セマンティクスに従い **`PATCH`** を採用しています。
> もし「全フィールドを必須にして丸ごと差し替える」設計にするなら `PUT` を使います。

### 動作確認

```bash
curl -s -X PATCH "http://backend:8000/api/v1/users/1" \
  -H "Content-Type: application/json" \
  -d '{"avatar_url": "https://example.com/new.png"}' | jq .
# avatar_url だけが更新され、他のフィールドはそのまま
```

---

## 12. ユーザー削除 API（Delete）

`DELETE /api/v1/users/{user_id}` で、ユーザーを削除します。

```python
# status_code=204 No Content: 削除成功時はボディなしが REST の慣習
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)

def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
) -> None:  # None: レスポンスボディが無いので戻り値も None
    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found (id={user_id})",
        )
    # User モデルの cascade="all, delete-orphan" 設定により、 紐づく Items も自動削除される
    session.delete(user)
    session.commit()
```

### 動作確認

```bash
curl -i -X DELETE "http://backend:8000/api/v1/users/1"
# HTTP/1.1 204 No Content
```

削除後に取得しようとすると 404：

```bash
curl -s "http://backend:8000/api/v1/users/1" | jq .
# {"detail": "User not found (id=1)"}
```

---

## 13. Swagger UI で全体を確認

http://localhost:8000/docs を開いて、実装した 5 つのエンドポイントを確認しましょう。

| メソッド | パス | 役割 |
|---|---|---|
| `POST` | `/api/v1/users/` | ユーザー作成 |
| `GET` | `/api/v1/users/{user_id}` | ユーザー取得 |
| `GET` | `/api/v1/users/` | ユーザー一覧 |
| `PATCH` | `/api/v1/users/{user_id}` | ユーザー更新 |
| `DELETE` | `/api/v1/users/{user_id}` | ユーザー削除 |

Swagger UI 上で：
- リクエストボディの形（`UserCreate` / `UserUpdate`）が自動表示される
- レスポンスの形（`UserRead`）が **schemas** セクションに展開される
- 各エンドポイントを **Try it out** で実行できる

---

## まとめ

この章では以下を学びました：

- **Pydantic スキーマ**でリクエスト・レスポンスを型付け（`Base/Create/Update/Read` の命名規則）
- **`pwdlib`** で Argon2 によるパスワードハッシュ化
- **`Depends(get_session)`** で DB セッションを依存性注入
- **`APIRouter` + `prefix="/api/v1"`** で API バージョニング
- **CRUD 5 つの基本パターン**: 201 Created / 200 OK / 200 OK / 200 OK / 204 No Content
- **`response_model`** と **`from_attributes=True`** の連携で SQLAlchemy モデルをそのまま返す

次章では、この CRUD API に **ID/PW 認証 + JWT トークン** を被せていきます。具体的には：

- ログイン API（`POST /api/v1/token`）でトークン発行
- 認証ガード（`Depends(get_current_user)`）で「認証済みユーザーだけが API を叩ける」状態にする
- JWT を **httpOnly Cookie** で扱う（XSS 対策）
- ロールベースの認可（特定のロールを持つユーザーだけがアクセスできるエンドポイント）
- Item の CRUD を **「ログインユーザーが自分の Item を管理する」** 形で実装

---

## 次の章

[Chapter 6: 認証・認可（自前ID/PW） →](../chapter06/README.md)
