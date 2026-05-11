# Chapter 7: 構造化ログとエラーハンドリング

[← 目次に戻る](../README.md)

## この章のゴール

- **構造化ログ (Structured Logging)** がなぜ必要かを理解する
- **structlog** で JSON 形式のログを出力する
- **リクエスト ID** をミドルウェアで自動付与し、全ログとレスポンスヘッダに含める
- **エラーハンドリング** を整備し、500 エラー時にスタックトレースをログに残しつつユーザーには安全なレスポンスを返す
- ログに **何を出力すべきか** の指針（高カーディナリティ・高ディメンション）を学ぶ

## スタート地点

```bash
git checkout chapter07-start
```

## 完成形

```bash
git checkout chapter07-end
```

---

## はじめに

Chapter 6 までで、認証・認可付きの CRUD API が動く状態になりました。しかし現状では：

- ログが `print()` レベル（構造がバラバラ、検索しづらい）
- エラー発生時にスタックトレースがそのままレスポンスに含まれることがある
- **「どのリクエストで何が起きたか」を後から追跡する手段がない**

本番運用に耐えるためには「**構造化されたログ**」と「**統一的なエラーハンドリング**」の 2 つが不可欠です。

---

## 1. なぜ構造化ログが必要か

### 従来のログの問題

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"User {user.username} created item {item.id}")
```

出力：
```
INFO:app.routers:User yamada created item 42
```

人間が読むぶんには問題ないですが、**本番環境で数千万行のログから特定のリクエストを探す** 場面では致命的に非効率です。

問題点：
- **構造が自由形式** … `User yamada created item 42` を機械的にパースして `username=yamada`, `item_id=42` を取り出すのが困難
- **検索・集計ができない** … 「yamada が過去 1 時間に何件 item を作成したか」を調べようとしても、正規表現で頑張るしかない
- **コンテキストが欠落** … リクエスト ID、処理時間、ユーザー ID などの共通情報がログに含まれない

### 構造化ログ

```json
{
  "event": "item_created",
  "username": "yamada",
  "item_id": 42,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-05-11T12:00:00.000Z",
  "level": "info"
}
```

- **JSON 形式** … 任意のフィールドでフィルタ・集計可能
- **構造が一定** … ログ基盤（CloudWatch Logs Insights, Datadog, Loki, Elasticsearch など）でそのまま検索できる
- **コンテキストを自動付与** … リクエスト ID、タイムスタンプ、ログレベルなどが毎行に含まれる

### ログに何を出力すべきか

ログに含める情報は「**後から調査するときに何が必要か**」から逆算します。オブザーバビリティの世界では以下の 2 つの性質が重要とされています。

#### 高カーディナリティ (High Cardinality)

**値のバリエーションが多い属性**。例：

- **リクエスト ID** (UUID) … リクエストごとに一意。「この 1 件のリクエストだけを追跡したい」ときに必須
- **ユーザー ID** … 「特定のユーザーに起きた問題を調べたい」ときに必要
- **Item ID** … 「特定のリソースに対する操作を追いたい」

「`level=info` で絞る」だけだと数百万件ヒットしますが、「`request_id=550e8400...` で絞る」と 1 件だけヒットします。高カーディナリティな値があるほど **ピンポイントで追跡できる** ということです。

#### 高ディメンション (High Dimensionality)

**属性（フィールド）の種類が多い**こと。例：

- `method`, `path`, `status_code`, `duration_ms`, `user_id`, `request_id`, `ip`, `user_agent`, ...

フィールドが多いほど「`status_code=500 AND path=/api/v1/items/ AND method=POST`」のような **多面的な検索** ができるようになります。

#### 本教材でログに含める情報

| フィールド | カーディナリティ | 用途 |
|---|---|---|
| `request_id` | 非常に高（UUID） | リクエスト単位の追跡 |
| `method` | 低（GET/POST/PATCH/DELETE） | HTTP メソッドでのフィルタ |
| `path` | 中 | どのエンドポイントが呼ばれたか |
| `status_code` | 低 | エラー率の監視 |
| `duration_ms` | 高 | パフォーマンス監視 |
| `user_id` | 高 | 特定ユーザーの問題追跡 |
| `level` | 低 | ログレベルでのフィルタ |
| `event` | 中 | 何が起きたかの説明 |

---

## 2. structlog のインストールと初期設定

### インストール

```bash
cd $PROJECT_DIR/backend
uv add 'structlog~=25.5.0'
```

### ログ設定ファイルを作成

```bash
touch $PROJECT_DIR/backend/app/logging_config.py
```

```python
# backend/app/logging_config.py
"""structlog の設定。アプリ起動時に 1 回呼ぶ。"""
import logging
import structlog


def setup_logging() -> None:
    """structlog を設定する。"""
    # structlog のプロセッサチェーン（ログイベントが通るパイプライン）
    structlog.configure(
        processors=[
            # コンテキスト変数をイベントに追加
            structlog.contextvars.merge_contextvars,
            # ログレベルを付与
            structlog.stdlib.add_log_level,
            # タイムスタンプを付与 (ISO 8601, UTC)
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # スタックトレースがあればフォーマット
            structlog.processors.StackInfoRenderer(),
            # 例外情報をフォーマット
            structlog.processors.format_exc_info,
            # JSON にレンダリング
            structlog.processors.JSONRenderer(),
        ],
        # structlog のロガーを標準 logging と統合
        wrapper_class=structlog.stdlib.BoundLogger,
        # キャッシュ有効化（パフォーマンス）
        cache_logger_on_first_use=True,
    )

    # 標準 logging のレベル設定（uvicorn のログなど）
    logging.basicConfig(level=logging.INFO, format="%(message)s")
```

### 解説

- **`processors`**: ログイベントが通る「パイプライン」。イベントが生成されてから JSON として出力されるまでに、タイムスタンプ追加やレベル追加などの加工を順番に通す
- **`merge_contextvars`**: Python の `contextvars` に格納された値（リクエスト ID など）を自動でログイベントにマージする。後のセクションで活用する
- **`JSONRenderer()`**: 最終的に JSON 文字列として出力する。本番ではこれが必須。開発時は `ConsoleRenderer()` に切り替えると見やすい
- **`TimeStamper(fmt="iso", utc=True)`**: ISO 8601 形式のタイムスタンプを UTC で付与。タイムゾーンに依存しないので、異なるリージョンのサーバー間でもログの時系列が正確に揃う

### main.py で呼ぶ

```python
# backend/app/main.py (冒頭に追加)
from app.logging_config import setup_logging

setup_logging()

# ... 以降は既存のコード ...
```

---

## 3. リクエスト ID の付与

### 3.1 ミドルウェアの実装

「リクエストごとに一意の ID を生成して、全ログとレスポンスヘッダに含める」ミドルウェアを実装します。

```bash
touch $PROJECT_DIR/backend/app/middleware.py
```

```python
# backend/app/middleware.py
"""カスタムミドルウェア。"""
import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """リクエストごとにリクエスト ID を付与し、アクセスログを出力する。"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # リクエスト ID を生成
        request_id = str(uuid.uuid4())

        # FastAPI(uvicorn)はリクエストを処理するworkerを再利用するため、以前のリクエストのcontextvarsを消去します
        structlog.contextvars.clear_contextvars()

        # リクエスト用の contextvars をバインド（以降このリクエスト内の全ログに自動付与される）
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # 処理時間の計測開始
        start_time = time.perf_counter()

        # リクエスト処理を実行
        response = await call_next(request)

        # 処理時間を計算
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # レスポンスヘッダにリクエスト ID を追加
        response.headers["X-Request-ID"] = request_id

        # アクセスログを出力
        await logger.ainfo(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
```

### 3.2 main.py に登録

```python
# backend/app/main.py (ミドルウェア登録を追加)
from app.middleware import RequestLoggingMiddleware

# ... setup_logging() の後、app.include_router() の前 ...

app.add_middleware(RequestLoggingMiddleware)
```

### 解説

- **`uuid.uuid4()`**: リクエストごとにランダムな UUID を生成。高カーディナリティで追跡に最適
- **`structlog.contextvars.bind_contextvars(request_id=...)`**: `contextvars` にバインドした値は、**このリクエスト処理中のあらゆるログに自動でマージ** される。エンドポイント内で `logger.info("something")` を呼んでも `request_id` が自動で含まれる
- **`clear_contextvars()`**: 前のリクエストのコンテキストが残らないようにリセット
- **`X-Request-ID` ヘッダ**: フロントエンドが「このリクエストでエラーが出た」と問い合わせるときに、このヘッダの値を伝えればバックエンドのログをピンポイントで特定できる
- **`duration_ms`**: パフォーマンス監視の基本。レスポンスが遅いエンドポイントを特定するのに使う

> **`contextvars` とは？**  
> Python 3.7 で標準ライブラリに追加された「**実行コンテキスト（リクエスト / async タスク）ごとに独立した値を保持する仕組み**」です。
>
> Web アプリで「リクエスト ID を全ログに含めたい」ときの問題：
> - 関数の引数でバケツリレーするのは面倒（呼び出し階層が深いと全関数に引数を足す必要がある）
> - グローバル変数に入れると、同時に処理される別リクエストの値と混ざってしまう
>
> `contextvars` は **「グローバル変数のように使えるが、リクエストごとに独立した値を持てる」** ことでこの問題を解決します。
>
> ```python
> # ミドルウェアでセット
> structlog.contextvars.bind_contextvars(request_id="aaa")
>
> # どの関数でも logger を呼ぶだけで request_id が自動で含まれる
> logger.info("user_created", user_id=1)
> # → {"event": "user_created", "user_id": 1, "request_id": "aaa", ...}
> ```
>
> 同時に処理されるリクエスト B で `bind_contextvars(request_id="bbb")` を呼んでも、リクエスト A のログには `"aaa"` が付いたまま混ざりません。Python の `asyncio` でも `await` をまたいでコンテキストが維持されるので、FastAPI の async エンドポイント内でも正しく動作します。

### 出力例

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "request_completed",
  "method": "GET",
  "path": "/api/v1/users/",
  "status_code": 200,
  "duration_ms": 12.34,
  "level": "info",
  "timestamp": "2026-05-11T12:00:00.000000Z"
}
```

---

## 4. アプリケーション内でのログ出力

エンドポイントやサービスロジックの中でもログを出力できます。`request_id` は `contextvars` 経由で **自動的に含まれる** ので、わざわざ引数で渡す必要がありません。

```python
# backend/app/routers.py (例: create_user 内)
import structlog

logger = structlog.get_logger()


@router.post("/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.USER_CREATE])),
) -> User:
    # ... 既存の実装 ...

    session.add(user)
    session.commit()
    session.refresh(user)

    # ビジネスイベントのログ
    logger.info("user_created", user_id=user.id, username=user.username)

    return user
```

出力：
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "user_created",
  "user_id": 1,
  "username": "yamada",
  "level": "info",
  "timestamp": "2026-05-11T12:00:00.000000Z"
}
```

`request_id` を明示的に渡していないのに含まれている点に注目してください。これが `contextvars` の力です。

### ログレベルの使い分け

| レベル | 用途 | 例 |
|---|---|---|
| **`debug`** | 開発時のデバッグ情報。本番では通常出力しない | 「SQL が何件 SELECT した」 |
| **`info`** | 正常系のビジネスイベント | 「ユーザーが作成された」「ログインした」 |
| **`warning`** | 異常だが回復可能な事象 | 「リクエストが rate limit に近づいている」 |
| **`error`** | エラー。人間の対応が必要な可能性がある | 「外部 API 呼び出しがタイムアウトした」 |
| **`critical`** | 致命的エラー。サービスが停止する可能性 | 「DB 接続プールが枯渇した」 |

> **ログを出しすぎない**  
> ログは出せば出すほどコスト（ストレージ、ネットワーク、分析負荷）がかかります。「**この情報が無いと問題を調査できない**」という情報だけを `info` 以上で出し、詳細は `debug` に留めるのが運用のコツです。

---

## 5. エラーハンドリング

### 5.1 現状の問題

FastAPI のデフォルトでは：

- **`HTTPException` を raise** → `{"detail": "..."}` が返る（これは良い）
- **未処理の例外（バグ）** → スタックトレースがそのままレスポンスに含まれることがある（**セキュリティ上NG**）
- **例外の詳細がログに残らない** → 「何が起きたか分からない」

### 5.2 カスタム例外ハンドラの実装

未処理の例外（500 Internal Server Error）をキャッチし、**ログにスタックトレースを残しつつ、ユーザーには安全なレスポンスを返す** ハンドラを実装します。

- [Install custom exception handlers | FastAPI](https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers)

```bash
touch $PROJECT_DIR/backend/app/exception_handlers.py
```

```python
# backend/app/exception_handlers.py
"""グローバルな例外ハンドラ。"""
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI アプリにカスタム例外ハンドラを登録する。"""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """未処理の例外をキャッチし、500 を返す。

        - ユーザーには汎用メッセージだけ返す（スタックトレースを漏らさない）
        - ログにはスタックトレース含む詳細を残す
        """
        logger.error(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            exc_info=exc,  # structlog がスタックトレースをフォーマットしてくれる
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )
```

### 5.3 main.py に登録

```python
# backend/app/main.py
from app.exception_handlers import register_exception_handlers

# ... app = FastAPI() の後 ...

# カスタム例外ハンドラ (補足されていないエラーが発生した際に、ログを出しつつ安全なレスポンスを返す)
register_exception_handlers(app)
```

### 解説

- **`@app.exception_handler(Exception)`**: FastAPI の他のハンドラ（`HTTPException` 用など）で処理されなかった全ての例外をキャッチする
- **ログには `exc_info=exc` を渡す**: structlog がスタックトレースを整形して JSON に含めてくれる
- **レスポンスは汎用メッセージだけ**: 攻撃者にバグの詳細（ファイルパス、変数の値など）を教えない

### 出力例（ログ側）

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "unhandled_exception",
  "exc_type": "ZeroDivisionError",
  "exc_message": "division by zero",
  "exception": "Traceback (most recent call last):\n  File ...\nZeroDivisionError: division by zero",
  "level": "error",
  "timestamp": "2026-05-11T12:00:00.000000Z"
}
```

レスポンス（ユーザー側）：
```json
{"detail": "Internal Server Error"}
```

スタックトレースはログに残るが、ユーザーには**一切漏れない**。運用チームはリクエスト ID でログを引けば詳細を確認できます。

---

## 6. 開発 / 本番のログフォーマット切り替え

開発環境では JSON ログは読みにくいので、**人間が読みやすいカラー出力** に切り替えられるようにします。

### config.py に追加

```python
# backend/app/config.py (追記)

class Environment(BaseSettings):
    # ... 既存のフィールド ...

    # ログフォーマット
    log_format: str = "json"  # "json" or "console"
```

### logging_config.py を修正

```python
# backend/app/logging_config.py
import logging
import structlog

from app.config import env


def setup_logging() -> None:
    """structlog を設定する。"""
    # 共通のプロセッサ
    shared_processors: list = [
        # コンテキスト変数をイベントに追加
        structlog.contextvars.merge_contextvars,
        # ログレベルを付与
        structlog.stdlib.add_log_level,
        # タイムスタンプを付与 (ISO 8601, UTC)
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # スタックトレースがあればフォーマット
        structlog.processors.StackInfoRenderer(),
        # 例外情報をフォーマット
        structlog.processors.format_exc_info,
    ]

    # レンダラを環境変数で切り替え
    if env.log_format == "console":
        # 開発環境: カラー付きの読みやすいフォーマット
        shared_processors.append(structlog.dev.ConsoleRenderer())
    else:
        # 本番環境: JSON
        shared_processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        # プロセッサチェーン（ログイベントが通るパイプライン）
        processors=shared_processors,
        # structlog のロガーを標準 logging と統合
        wrapper_class=structlog.stdlib.BoundLogger,
        # キャッシュ有効化（パフォーマンス）
        cache_logger_on_first_use=True,
    )

    # 標準 logging のレベル設定（uvicorn のログなど）
    logging.basicConfig(level=logging.INFO, format="%(message)s")
```

### .env.sample に追加

```bash
# backend/.env.sample (追記)

# 開発は console (カラー出力)、本番は json
LOG_FORMAT=console
```

開発環境では `LOG_FORMAT=console` にしておくと、ターミナルでのログが格段に読みやすくなります。

---

## 7. main.py の全体像

ここまでの変更を反映した `main.py` の全体像：

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import setup_logging
from app.exception_handlers import register_exception_handlers
from app.middleware import RequestLoggingMiddleware
from app.routers import router

# ログ設定（最初に呼ぶ）
setup_logging()

app = FastAPI()

# 例外ハンドラ登録 (補足されていないエラーが発生した際に、ログを出しつつ安全なレスポンスを返す)
register_exception_handlers(app)

# ミドルウェア登録（登録順の逆順で実行される）

# ミドルウェア: リクエストごとにリクエスト ID を付与し、アクセスログを出力する
app.add_middleware(RequestLoggingMiddleware)

# ミドルウェア: CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Hello World"}
```

> **ミドルウェアの登録順序**  
> Starlette / FastAPI のミドルウェアは **最後に登録したものが最初に実行** されます（スタック構造）。CORS → RequestLogging の順で登録しているので、実行は RequestLogging → CORS の順になります。

---

## 8. 動作確認

### .env の更新とコンテナ再起動

`.env.sample` に `LOG_FORMAT` を追加したので、`.env` を再生成してからコンテナを再ビルドします。

```bash
cd $PROJECT_DIR

# .env を再生成（LOG_FORMAT などの追加分を反映）
envsubst < $PROJECT_DIR/backend/.env.sample > $PROJECT_DIR/backend/.env

# .env をシェルの環境変数として export
export $(grep -v '^#' $PROJECT_DIR/backend/.env | xargs)

# コンテナを停止・削除してから再ビルド＆起動
docker compose down && docker compose up -d --build

cd $PROJECT_DIR/backend

# マイグレーション（テーブルが無ければ作成）
uv run alembic upgrade head

# シードデータの投入
uv run python -m app.seed
```

### コンテナログを tail する

**ターミナルを 2 つ開いて** ください。1 つ目でログを監視し、2 つ目から API を叩いて確認します。

**ターミナル 1（ログ監視）:**

```bash
cd $PROJECT_DIR
docker compose logs -f backend
```

### アクセスログの確認

**ターミナル 2（API 呼び出し）:**

```bash
export $(grep -v '^#' $PROJECT_DIR/backend/.env | xargs)

TOKEN=$(curl -s -X POST "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/v1/login?username=sys_admin&password=admin" | jq -r .access_token)
curl -s -H "Authorization: Bearer $TOKEN" "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/v1/users/" > /dev/null
```

ログに以下のような JSON が出力されます：

```json
 {"method": "GET", "path": "/api/v1/users/", "status_code": 200, "duration_ms": 8.62, "event": "request_completed", "request_id": "51c5692a-9db1-42f2-84ae-6367b3bbbe01", "level": "info", "timestamp": "2026-05-11T13:01:02.556826Z"}
```

### レスポンスヘッダの確認

```bash
curl -i -H "Authorization: Bearer $TOKEN" "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/v1/users/"
# ...
# x-request-id: 550e8400-e29b-41d4-a716-446655440000
# ...
```

`X-Request-ID` ヘッダがレスポンスに含まれていることを確認。

### 500 エラーのテスト

一時的にエンドポイント内でわざと例外を発生させて、ログとレスポンスを確認してみましょう。

```python
# 一時的に routers.py に追加（確認後削除）
@router.get("/test-error")
def test_error():
    raise RuntimeError("This is a test error")
```

```bash
curl -s "http://web-tutorial-v2-backend-${HOST_USER}:8000/api/v1/test-error" | jq .
# {"detail": "Internal Server Error"}
```

ログ側：
```json
{"exc_type": "RuntimeError", "exc_message": "This is a test error", "event": "unhandled_exception", "request_id": "c545c5be-e312-48ae-9ee7-fd3d51d7d487", "level": "error", "timestamp": "2026-05-11T13:02:46.831894Z", "exception": "..."}
```

ユーザーにはスタックトレースが**一切漏れていない**が、ログには**完全なトレース**が残っている。これが理想的なエラーハンドリングです。

---

## まとめ

この章では以下を学びました：

- **構造化ログの必要性**: JSON 形式にすることで検索・集計・監視が可能に
- **高カーディナリティ / 高ディメンション**: ログに何を含めるべきかの指針
- **structlog**: Python の構造化ログライブラリ。プロセッサチェーンで加工、`contextvars` でリクエストスコープの値を自動付与
- **リクエスト ID**: UUID をミドルウェアで生成し、全ログ + レスポンスヘッダ `X-Request-ID` に含める。問題追跡の要
- **エラーハンドリング**: 未処理例外をキャッチし、ログにスタックトレースを残しつつユーザーには安全なレスポンスを返す
- **開発 / 本番切り替え**: `LOG_FORMAT` 環境変数で JSON / カラーコンソールを切り替え

次章では、ここまで実装した API の **自動テスト (pytest)** を書いていきます。

---

## 次の章

[Chapter 8: API テスト (pytest) →](../chapter08/README.md)
