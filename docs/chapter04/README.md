# Chapter 4: Alembic によるマイグレーション

[← 目次に戻る](../README.md)

## この章のゴール

- **マイグレーション** がなぜ必要なのかを理解する
- `pydantic-settings` で型付きの設定オブジェクトを作り、環境変数を読み込めるようにする
- Chapter 3 で Notebook 上に書いた SQLAlchemy モデルを **`backend/app/` 配下に正式に配置** する
- **Alembic** プロジェクトを作成し、初期スキーマのマイグレーションを生成・適用する
- マイグレーションファイル内に **`updated` 自動更新トリガー** を埋め込む
- **シードデータ（初期データ）** を冪等な別スクリプトとして実装し、`roles` テーブルに固定 3 件を投入する
- モデルを変更（`users.avatar_url` カラムを追加）し、新しいマイグレーションを生成・適用するサイクルを体験する

## スタート地点

```bash
git checkout chapter04-start
```

## 完成形

```bash
git checkout chapter04-end
```

---

## はじめに

Chapter 3 では、Notebook で `Base.metadata.create_all(engine)` を呼ぶことで、Python のモデル定義から DB のテーブルを作りました。これは学習用には便利ですが、**実運用には致命的な問題があります**。

開発を進めると、テーブル定義は何度も変更されます。例えば「`users` テーブルにプロフィール画像の URL を保存するカラムを追加したい」となったとき、Python のモデル変更を **本番 DB にどう反映するか** が問題になります。

### 手動で `ALTER TABLE` を打つアプローチの問題

DB にログインして `ALTER TABLE users ADD COLUMN avatar_url TEXT;` のような SQL を直接実行する方法は、以下の理由で **避けるべき** です：

1. **どの環境にどこまで適用したかが分からなくなる**  
   開発環境・ステージング環境・本番環境のように複数の環境がある場合、「ある変更がどの環境まで適用済みか」を正確に把握するのは困難です。
2. **変更履歴がソースコードに残らない**  
   いつ・誰が・どんな変更をしたかが追跡できないので、レビューもロールバックもできません。
3. **チーム開発で同期できない**  
   別のメンバーが pull したコードのモデル定義と、自分の DB のスキーマがずれていても、それに気づく仕組みがありません。

### 解決策: マイグレーションツール

これらの問題を解決するのが **DB マイグレーションツール** です。Python では [Alembic](https://alembic.sqlalchemy.org/) が SQLAlchemy 公式のツールとして広く使われています。

Alembic を使うと：

- **モデルの差分から SQL を自動生成** できる（autogenerate）
- 変更を **マイグレーションファイルとしてリポジトリにコミット** できる
- 各環境で `alembic upgrade head` を実行すれば、未適用の変更だけが順番に流れる
- **ロールバック** も `alembic downgrade -1` で簡単

この章では Alembic プロジェクトを作って、Chapter 3 のモデルを正式にマイグレーション管理する流れを体験します。

---

## 1. 環境変数を読み込む

この章でも Chapter 3 と同じく、`backend/.env` の値をシェルの環境変数として読み込んでおきます。Dev Container のターミナルを開き直した場合や、新しいシェルから作業する場合は、毎回この手順が必要です。

```bash
cd $PROJECT_DIR

# .env が無ければ生成 (Chapter 3 で生成済みならスキップ)
test -f $PROJECT_DIR/backend/.env || envsubst < $PROJECT_DIR/backend/.env.sample > $PROJECT_DIR/backend/.env

# .env をシェルの環境変数として export
export $(grep -v '^#' $PROJECT_DIR/backend/.env | xargs)

# 確認
echo $DB_HOST
# web-tutorial-v2-db-ktamido のように表示されればOK
```

> **シェルを開き直すたびに `export` が必要**  
> `export` した環境変数は **そのシェルセッション内でしか有効になりません**。VS Code のターミナルを閉じ直したり、別のターミナルを開いた場合は再度 `export` してください。

---

## 2. DB を綺麗な状態にする

Chapter 3 では Notebook で `Base.metadata.create_all(engine)` を実行したり、生 SQL でテーブルを作ったりしました。Alembic を使うときは「**最初は空の DB から始めて、マイグレーションだけがスキーマを作る**」という前提が大事なので、ここで DB をリセットします。

```bash
cd $PROJECT_DIR

# 既存コンテナを破棄して、 db を含めた全サービスを再ビルドして起動
# (永続化ボリュームを設定していないので、 db の中身もコンテナ破棄で消える)
docker compose down
docker compose up -d --build

# 確認: テーブルが空であること
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\dt'
# Did not find any relations.
```

> **永続化ボリュームを設定していないので、コンテナを破棄するだけで DB が綺麗になります。**

---

## 3. 環境変数を扱う設定オブジェクト

Chapter 3 では Notebook で `os.environ["DB_USER"]` のように直接環境変数を読みました。Alembic から読むコードと FastAPI から読むコードの両方で同じことを書くのは冗長なので、ここで **設定オブジェクト** にまとめます。

`pydantic-settings` を使うと、**環境変数を型付きの Pydantic モデル** として扱えます。型がチェックされ、欠けている値があれば起動時にエラーになるので、ハマりが減ります。

### pydantic-settings をインストール

```bash
cd $PROJECT_DIR/backend
uv add 'pydantic-settings~=2.14.0'
```

### config.py を作成

```bash
mkdir -p $PROJECT_DIR/backend/app
touch $PROJECT_DIR/backend/app/config.py
```

```python
# backend/app/config.py
from pydantic_settings import BaseSettings


class Environment(BaseSettings):
    """環境変数から読み込まれる設定オブジェクト"""

    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str

    @property
    def database_url(self) -> str:
        """SQLAlchemy 用の接続 URL を組み立てる"""
        return f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


env = Environment()  # type: ignore[call-arg]
```

### 解説

- **`BaseSettings`** … `pydantic-settings` が提供する基底クラス。インスタンス化時に **環境変数を自動で読み込んで** フィールドにセットする
- **属性名は小文字（`db_user`）、環境変数は大文字 (`DB_USER`)** … `pydantic-settings` は **大文字小文字を区別せず** 環境変数名と属性名をマッチさせるので、Python 慣習どおりに小文字で書ける
- **`database_url`** … `@property` で SQLAlchemy 用の接続 URL を組み立てている。ここを 1 箇所にまとめておけば、Alembic からも FastAPI アプリからも同じロジックを使える
- **`# type: ignore[call-arg]`** … `BaseSettings` のサブクラスは引数なしで初期化できるが、mypy/Pylance はそれを認識できないので警告を抑制している

### 動作確認

`.env` を export 済みの状態で：

```bash
cd $PROJECT_DIR/backend
uv run python -c "from app.config import env; print(env.database_url)"
# postgresql+psycopg://app:app_pass@web-tutorial-v2-db-ktamido:5432/app
```

---

## 4. Engine と Session を定義する

Chapter 3 では Notebook で `engine` と `SessionLocal` を作りましたが、これも **モジュールに切り出す** ことで、Alembic からもアプリからも使い回せるようにします。

```bash
touch $PROJECT_DIR/backend/app/session.py
```

```python
# backend/app/session.py
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
```

### 解説

- **`get_session()`** … FastAPI の依存性注入 (`Depends`) で使うことを想定したジェネレータ関数。**`yield` で セッションを渡し、リクエスト処理が終わったら `finally` で必ず `close()`** する
- 後の Chapter 5（CRUD）で `def some_route(session: Session = Depends(get_session))` のように使います

---

## 5. モデルを定義する

Chapter 3 の Notebook で書いたモデル定義を、`backend/app/model.py` に正式に配置します。

```bash
touch $PROJECT_DIR/backend/app/model.py
```

```python
# backend/app/model.py
import enum
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RoleType(str, enum.Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    LOCATION_ADMIN = "LOCATION_ADMIN"
    LOCATION_OPERATOR = "LOCATION_OPERATOR"


def now_utc() -> datetime:
    """タイムゾーン付きの現在時刻 (UTC) を返す"""
    return datetime.now(timezone.utc)


class User(Base):
    """users テーブル"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    items: Mapped[list["Item"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class Item(Base):
    """items テーブル"""
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(String(128))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, user_id={self.user_id}, title={self.title})>"


class Role(Base):
    """roles テーブル"""
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[RoleType] = mapped_column(
        Enum(RoleType, name="role_type"),
        unique=True,
        index=True,
    )
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    users: Mapped[list["User"]] = relationship(
        secondary="user_roles",
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class UserRole(Base):
    """users と roles の中間テーブル"""
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="unique_idx_userid_roleid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
```

### DB 側のカラム型を明示する

`mapped_column(...)` の **第 1 引数** には、SQLAlchemy のカラム型を渡せます。本教材では「**暗黙より明示**」の方針で、すべてのカラムに型を明示しています。

| Python 型 | 暗黙の SQLAlchemy 型 | 明示する型の例 | DB 側の型（PostgreSQL） |
|---|---|---|---|
| `int` | `Integer` | `Integer` | `INTEGER` |
| `str` | `String`（長さ無し VARCHAR） | `String(255)` 等 | `VARCHAR(255)` |
| `datetime` | `DateTime`（タイムゾーン無し） | `DateTime(timezone=True)` | `TIMESTAMP WITH TIME ZONE` (`TIMESTAMPTZ`) |

### 解説

- **`Integer`** は明示しなくても `Mapped[int]` から推論されますが、**他の型と表記を揃える**ために明示しています
- **`String(255)`** … 長さを明示しています。これを書かないと `VARCHAR`（長さ無し）になり、PostgreSQL では動きますが MySQL や SQL Server では `CREATE TABLE` 時にエラーになります。**`username`/`hashed_password` は 255 文字、`title` は 64 文字、`content` は 128 文字** など、用途に応じた長さを設定しています
- **`DateTime(timezone=True)`** … 第 2 部の生 SQL で使った `TIMESTAMPTZ` と同じ型を明示的に指定。これを書かないと `TIMESTAMP WITHOUT TIME ZONE` になってしまい、Chapter 3 で議論した「タイムゾーン情報を保持する」原則と矛盾します
- **`Enum(RoleType, name="role_type")`** … 第 2 部で `CREATE TYPE role_type AS ENUM (...)` で作った Enum 型に対応。`name="role_type"` で PostgreSQL 上の Enum 型名を明示

> **「暗黙の型推論」が動く場面と「明示すべき」場面**  
> SQLAlchemy 2.0 の `Mapped[型]` から自動推論される型は便利ですが、**プロジェクトとして DB 側のスキーマを正確にコントロールしたい場合は明示する** のが安全です。特に：
>
> - **`str` → `String` (長さ無し)**: PostgreSQL なら動くが、他の DB に移植した瞬間に動かなくなる
> - **`datetime` → `DateTime` (タイムゾーン無し)**: タイムゾーン付きが欲しいなら絶対に明示が必要
>
> 学習教材としては「**Mapped[...] の型ヒントは Python 側のための情報、`mapped_column(...)` の第 1 引数は DB 側の型を決める情報**」と整理して使い分けると認知が綺麗です。

> Chapter 3 の Notebook で書いたモデルとほぼ同じ構造ですが、**DB 側の型を明示する** 点が変わっています。Notebook 上では `Base.metadata.create_all(engine)` で手元の DB に作るだけだったので暗黙でも動きましたが、Alembic で管理する以上は **生成される SQL が意図通りになる** ことを保証したいので、明示する形にしました。

---

## 6. Alembic プロジェクトを作成する

### 6.1 Alembic をインストール

```bash
cd $PROJECT_DIR/backend
uv add 'alembic~=1.18.4'
```

### 6.2 Alembic プロジェクトの初期化

`backend/` ディレクトリで `alembic init` を実行します。これにより `backend/alembic/` ディレクトリと `backend/alembic.ini` が生成されます。

```bash
cd $PROJECT_DIR/backend
uv run alembic init alembic
```

生成されるファイル：

```
backend/
├── alembic.ini             # Alembic の設定ファイル
└── alembic/
    ├── env.py              # マイグレーション実行時の Python 設定 (engine, metadata 等)
    ├── README
    ├── script.py.mako      # マイグレーションファイルのテンプレート
    └── versions/           # 個々のマイグレーションファイルが入る
```

> **`alembic init` のテンプレート**  
> `alembic init -t async alembic` のように `-t` でテンプレートを切り替えられます。今回は同期 SQLAlchemy を使うので、デフォルトの `generic` で OK です。

### 6.3 alembic.ini を編集

`alembic.ini` の `sqlalchemy.url` の行を **コメントアウト** します。接続 URL は `env.py` から実行時に上書きする方針にするため、`alembic.ini` の固定値は使いません。

```ini
# backend/alembic.ini (生成された行のうち、変更が必要なのは下記のみ)

# (デフォルトでは下記のような行があるので、コメントアウトする)
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

その他のセクション（`[loggers]` `[handlers]` 等のロギング設定や `script_location` など）は **デフォルトのまま** で OK です。

> **なぜ `alembic.ini` に書かないのか？**  
> `alembic.ini` に直接接続 URL を書くと、**パスワードを git にコミットしてしまう** リスクがあります。代わりに `env.py` で `app.config.env.database_url` を参照すれば、`backend/.env` の値が使われ、リポジトリには値が残りません。

### 6.4 alembic/env.py を編集

`alembic/env.py` を以下の 3 箇所だけ変更します。

**(a) ファイル先頭付近に import を追加**

`from logging.config import fileConfig` などの import の下あたりに追記：

```python
# backend/alembic/env.py

import sys
from pathlib import Path

# alembic ディレクトリの 1 階層上 (= backend/) を sys.path に追加して、app.* を import 可能に
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import env as app_env
from app.model import Base
```

**(b) `target_metadata = None` の行を差し替え**

```python
# backend/alembic/env.py

target_metadata = Base.metadata
```

**(c) `target_metadata = Base.metadata` の直後に、URL を実行時に上書きする 1 行を追加**

```python
# backend/alembic/env.py

# alembic.ini の sqlalchemy.url を実行時に環境変数由来の URL で上書きする
config.set_main_option("sqlalchemy.url", app_env.database_url)
```

### 解説

- **`sys.path.insert(...)`** … Alembic は `backend/` ディレクトリ直下で実行されるが、Python の import 解決のために明示的にパスを通している
- **`Base.metadata`** … `model.py` で定義した全モデルの **テーブル定義の集合**。これを Alembic に教えることで、autogenerate がモデルと DB の差分を検出できる
- **`config.set_main_option("sqlalchemy.url", ...)`** … `alembic.ini` の値を **実行時に上書き** する公式推奨パターン。

> **オフラインモードとは？**  
> Alembic には「オンラインモード」と「オフラインモード」の 2 種類があります。
>
> - **オンラインモード** (`alembic upgrade head`) … 実際に DB に接続してマイグレーションを適用する通常の使い方
> - **オフラインモード** (`alembic upgrade head --sql`) … DB に接続せず、適用される SQL を標準出力に書き出すだけのモード。生成された SQL を DBA に渡して本番環境で手動実行する、といった運用で使われる
>
> どちらのモードも `config.get_main_option("sqlalchemy.url")` から URL を取るので、(c) の `set_main_option` 1 行で両方カバーできます。

---

## 7. 初期マイグレーションを生成する

モデルと DB の差分から、初期テーブル作成のマイグレーションを **autogenerate** で生成します。

```bash
cd $PROJECT_DIR/backend

# .env を export 済みであることを確認
echo $DB_HOST  # web-tutorial-v2-db-ktamido のように表示されればOK

# 初期マイグレーションを生成
uv run alembic revision --autogenerate -m "create initial table"
```

`backend/alembic/versions/XXXXXXXXXXXX_create_initial_table.py` というファイルが生成されます。中身を見てみましょう：

```python
# backend/alembic/versions/XXXXXXXXXXXX_create_initial_table.py
"""create initial table

Revision ID: da61d148b844
Revises: 
Create Date: 2026-05-08 17:56:38.184148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da61d148b844'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Enum('SYSTEM_ADMIN', 'LOCATION_ADMIN', 'LOCATION_OPERATOR', name='role_type'), nullable=False),
    sa.Column('created', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ... users, items, user_roles の create_table が続く ...


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_roles')
    op.drop_table('items')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_table('roles')
    # ### end Alembic commands ###

```

### 構造の解説

| 要素 | 役割 |
|---|---|
| `revision` | このマイグレーションの ID（ランダム生成） |
| `down_revision` | 1 つ前のマイグレーションの ID（初回は `None`） |
| `upgrade()` | このマイグレーションを **適用するとき** に実行される処理 |
| `downgrade()` | このマイグレーションを **取り消すとき** に実行される処理 |
| `op.create_table(...)` | テーブルを作成するヘルパー関数 |
| `op.drop_table(...)` | テーブルを削除するヘルパー関数 |

`upgrade()` の内容は「現在の DB 状態 → モデル定義の状態」への差分。`downgrade()` はその逆操作になっています。

---

## 8. updated 自動更新トリガーをマイグレーションに追加

Chapter 3 で各テーブルに **`set_<table>_updated_at` トリガー** を設定しました。これも DB スキーマの一部なので、Alembic で管理する必要があります。

ただし autogenerate は **トリガーや関数を検出しません**。手動で追記します。

生成されたマイグレーションファイルの `upgrade()` の **末尾** に以下を追加：

```python
def upgrade() -> None:
    # ... 既存の create_table ... (省略)

    # 共通のトリガー関数を作成
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated = CURRENT_TIMESTAMP;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 各テーブルにトリガーを設定
    for table_name in ("users", "items", "roles", "user_roles"):
        op.execute(f"""
            CREATE OR REPLACE TRIGGER set_{table_name}_updated_at
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
        """)
```

`downgrade()` の **先頭** に逆順の処理を追加します（テーブルが残っている間にトリガーを消す必要があるため）。トリガー本体はテーブルと一緒に削除されるので不要ですが、関数は明示的に削除します：

```python
def downgrade() -> None:
    # トリガー関数を削除 (テーブル削除前: テーブル削除でトリガーは自動削除されるが、
    # 関数自体はテーブルから独立しているので明示的に削除する)
    # ※ ただし関数を先に消すとテーブルのトリガーから依存されているため、
    #    テーブル → 関数 の順で消す必要がある

    # ... 既存の drop_table ... (autogenerate で生成された drop_table 群)

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
    sa.Enum(name="role_type").drop(op.get_bind())
```

> **autogenerate の限界**  
> autogenerate が検出できるのは **テーブル・カラム・インデックス・外部キー** の追加/削除/変更のみです。トリガー、ストアドプロシージャ、ビュー、関数などは検出されません。これらは `op.execute("...")` で手書きする必要があります。

---

## 9. マイグレーションを適用する

### 9.1 オフラインモードで実行される SQL を確認する

実際にマイグレーションを適用する前に、**Alembic がどんな SQL を発行しようとしているか** を確認しておきます。これは実務でも重要な習慣で、特に本番環境への適用前は **DBA や同僚に SQL をレビューしてもらってから適用** するケースが多いです。

Alembic の **オフラインモード** (`--sql` フラグ) を使うと、DB に接続せずに発行予定の SQL を標準出力に書き出すだけになります。

```bash
cd $PROJECT_DIR/backend

# オフラインモードで SQL を確認 (DB は変更されない)
uv run alembic upgrade head --sql
```

以下のような SQL が出力されます：

```sql
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INFO  [alembic.runtime.migration] Running upgrade  -> da61d148b844, create initial table
-- Running upgrade  -> da61d148b844

CREATE TYPE role_type AS ENUM ('SYSTEM_ADMIN', 'LOCATION_ADMIN', 'LOCATION_OPERATOR');

CREATE TABLE roles (
    id SERIAL NOT NULL, 
    name role_type NOT NULL, 
    created TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_roles_name ON roles (name);

CREATE TABLE users (
    id SERIAL NOT NULL, 
    username VARCHAR(255) NOT NULL, 
    hashed_password VARCHAR(255) NOT NULL, 
    created TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

-- ... items, user_roles の CREATE TABLE が続く ...


CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated = CURRENT_TIMESTAMP;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;;

CREATE OR REPLACE TRIGGER set_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();;

-- ... items, roles, user_roles のトリガー作成が続く ...

INSERT INTO alembic_version (version_num) VALUES ('da61d148b844') RETURNING alembic_version.version_num;

COMMIT;
```

意図した SQL になっているか確認しましょう。**自分が書いた `op.execute(...)` の中身も含めて、すべての DDL がここに展開** されているはずです。

> **オフラインモードのユースケース**  
> - **本番適用前のレビュー**: 上の出力をファイルに保存（`--sql > migration.sql`）して、PR でレビューしてもらう、DBA に渡す
> - **CI でドライラン**: 「マイグレーションが SQL として成立するか」を本番に触らずチェックできる
> - **手元と本番の DB ユーザーで権限が違う場合**: 手元では適用できないが、本番権限で実行する SQL を生成する

### 9.2 オンラインモードで実際に適用する

SQL の内容に問題がなければ、実際に DB に適用します。

```bash
uv run alembic upgrade head
```

`upgrade head` で「最新のリビジョンまで上げる」という意味です。

### 9.3 適用結果を確認

```bash
# Alembic の履歴を確認
uv run alembic history
# <base> -> da61d148b844 (head), create initial table

# 現在 DB に適用されているリビジョンを確認
uv run alembic current
# da61d148b844 (head)
```

DB に直接接続してテーブルを確認：

```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\dt'
#                List of relations
#  Schema |      Name       | Type  | Owner
# --------+-----------------+-------+-------
#  public | alembic_version | table | app  ← Alembic が自動で作る管理テーブル
#  public | items           | table | app
#  public | roles           | table | app
#  public | user_roles      | table | app
#  public | users           | table | app
```

> **`alembic_version` テーブル**  
> Alembic は **「現在 DB に適用されているリビジョン ID」を覚えておくため** に、`alembic_version` という管理テーブルを自動で作ります。`alembic upgrade` を実行するたびに、ここの値が更新されます。

トリガーの確認：

```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\df set_updated_at"
#                                List of functions
#  Schema |      Name       | Result data type | Argument data types | Type
# --------+-----------------+------------------+---------------------+------
#  public | set_updated_at  | trigger          |                     | func
```

これで **DB スキーマ** は完成しました。次は、アプリケーションが必要とする **シードデータ（初期データ）** を投入します。

---

## 10. シードデータ（初期データ）を投入する

アプリケーションの起動時に **必ず存在していてほしいレコード** があります。例えば `roles` テーブルの 3 件（`SYSTEM_ADMIN` / `LOCATION_ADMIN` / `LOCATION_OPERATOR`）は **Chapter 6 の認証・認可** で必須です。

このような **初期データ・固定データ** のことを **シードデータ (seed data)** と呼びます。

### 投入方法の選択

シードデータの投入方法は大きく 2 通りあります：

| 方式 | メリット | デメリット |
|---|---|---|
| **マイグレーションに含める** | DB の状態が「マイグレーション適用後 = 完成形」になる | データ修正のたびに新しいマイグレーションが必要、冪等性の管理が面倒 |
| **別スクリプトとして実装** | データ管理がスキーマと分離できる、冪等に書きやすい、環境ごとに違うデータも扱いやすい | 実行が必要なステップが 1 つ増える |

**本教材は別スクリプト方式を採用します**。理由：

- マイグレーションは「DB スキーマの履歴」、シードは「データの投入」と関心が異なる
- 後の章（Chapter 5 以降）で **開発・テスト用のサンプルデータ** や **管理者ユーザーの作成** など、シード系の処理が増えていく見込み。最初から別スクリプトにしておくと拡張しやすい
- 冪等な書き方（既に存在すればスキップ）を学べる

> **コラム: Alembic でシードデータを入れる方法もある**  
> 学習時の参考までに、マイグレーションに含める書き方も紹介しておきます（**本教材では採用しません**）。
>
> `op.bulk_insert(...)` を使うと、`create_table` の戻り値を使って一気にレコードを投入できます：
>
> ```python
> def upgrade() -> None:
>     roles_table = op.create_table("roles", ...)
>     # ...
>     now = datetime.now(timezone.utc)
>     op.bulk_insert(
>         roles_table,
>         [
>             {"id": 1, "name": "SYSTEM_ADMIN",      "created": now, "updated": now},
>             {"id": 2, "name": "LOCATION_ADMIN",    "created": now, "updated": now},
>             {"id": 3, "name": "LOCATION_OPERATOR", "created": now, "updated": now},
>         ],
>     )
>     # IDENTITY のシーケンスを進める (id を明示するとシーケンスが進まないため)
>     op.execute("SELECT setval(pg_get_serial_sequence('roles', 'id'), (SELECT MAX(id) FROM roles));")
> ```
>
> シンプルに見えますが、**冪等に書きづらい**（マイグレーション再実行で衝突する）、**データ修正のたびに新しいマイグレーションが必要**、といった運用上の難しさがあります。

### 10.1 seed.py を作成する

`backend/app/seed.py` を作って、ロールを投入する関数を実装します。

```bash
touch $PROJECT_DIR/backend/app/seed.py
```

```python
# backend/app/seed.py
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
```

### 解説

- **`if __name__ == "__main__":`** … このファイルが直接 `python -m app.seed` で呼ばれたときだけ `main()` を実行する Python の慣習
- **冪等性**: `RoleType` の各値ごとに、まず `SELECT` で存在を確認してから、無ければ `INSERT` する。何度実行しても結果が同じになる
- **`with SessionLocal() as session:`** … Chapter 3 で学んだセッションスコープ。ブロックを抜けるときに `close()` される
- **`session.add(Role(name=role_type))`** … `id` は IDENTITY で自動採番されるので指定不要。**シーケンスも自然に進む** ので「マイグレーション内 INSERT で id を固定する」方式の罠（シーケンスを手動で進める必要がある）も避けられる

### 10.2 seed.py を実行する

```bash
cd $PROJECT_DIR/backend
uv run python -m app.seed
# Seeding roles...
#   inserted: SYSTEM_ADMIN
#   inserted: LOCATION_ADMIN
#   inserted: LOCATION_OPERATOR
# Done.
```

もう 1 回実行してみると：

```bash
uv run python -m app.seed
# Seeding roles...
#   skipped (already exists): SYSTEM_ADMIN
#   skipped (already exists): LOCATION_ADMIN
#   skipped (already exists): LOCATION_OPERATOR
# Done.
```

何度実行してもエラーにならず、状態が変わらないことを確認できます。これが **冪等性 (idempotency)** です。

### 10.3 投入結果を確認

```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT * FROM roles"
--  id |       name        |            created            |            updated
-- ----+-------------------+-------------------------------+-------------------------------
--   1 | SYSTEM_ADMIN      | 2026-05-08 12:00:00.123456+00 | 2026-05-08 12:00:00.123456+00
--   2 | LOCATION_ADMIN    | 2026-05-08 12:00:00.123456+00 | 2026-05-08 12:00:00.123456+00
--   3 | LOCATION_OPERATOR | 2026-05-08 12:00:00.123456+00 | 2026-05-08 12:00:00.123456+00
```

3 件のロールが登録されています。

---

## 11. モデルを変更してマイグレーションを試す

ここからが Alembic の本領発揮です。**モデルを変更してマイグレーションを再生成・適用** する流れを体験します。

例として、**`users` テーブルに `avatar_url`（プロフィール画像の URL）カラムを追加** します。

### 11.1 モデルを変更

`backend/app/model.py` の `User` クラスに以下のカラムを追加します。**`TEXT` 型を使うので import も追加** します。

```python
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint  # ← Text を追加

# ... 既存のコード ...

class User(Base):
    """users テーブル"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text, default=None)  # ← 追加
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # ... 以下省略 ...
```

### 解説

- **`Mapped[str | None]`** … NULL 許容。プロフィール画像は登録必須にしたくないので Optional にする
- **`mapped_column(Text, ...)`** … URL は文字数の上限を決めかねる長い文字列があり得るため、上限のない `TEXT` 型を利用する
- **`default=None`** … モデルインスタンスを作るときに省略できるようにする

> **`VARCHAR(n)` と `TEXT` の使い分け**  
> PostgreSQL では **`VARCHAR(n)` と `TEXT` の性能差は基本ありません**。MySQL とは違い、`TEXT` 型を使ってもインデックスが張れますし、ストレージサイズも実データのバイト数+ヘッダで決まります。「長さの上限を決めたいか・決めなくて良いか」で選んで OK です。


### 11.2 マイグレーションを生成

```bash
cd $PROJECT_DIR/backend
uv run alembic revision --autogenerate -m "add avatar_url column to users"
```

生成されたファイル `backend/alembic/versions/XXXXXXXXXXXX_add_avatar_url_column_to_users.py` を確認：

```python
def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('avatar_url', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'avatar_url')
    # ### end Alembic commands ###

```

`add_column` 1 行だけのシンプルなマイグレーションが自動生成されました。

### 11.4 適用

```bash
# 履歴を確認すると新しいリビジョンが head になっている
uv run alembic history
# da61d148b844 -> 634e50af5a67 (head), add avatar_url column to users
# <base> -> da61d148b844, create initial table

# 現在のリビジョンはまだ initial table のまま
uv run alembic current
# da61d148b844

# 実行されるSQLを確認
uv run alembic upgrade da61d148b844:head --sql
# BEGIN;
# 
# -- Running upgrade da61d148b844 -> 634e50af5a67
# 
# ALTER TABLE users ADD COLUMN avatar_url TEXT;
# 
# UPDATE alembic_version SET version_num='634e50af5a67' WHERE alembic_version.version_num = 'da61d148b844';
# 
# COMMIT;

# マイグレーションを適用
uv run alembic upgrade head

# 最新のリビジョンに上がった
uv run alembic current
# 634e50af5a67 (head)
```

### 11.5 テーブルを確認

```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\d users'
#                                Table "public.users"
#      Column      |           Type           | Collation | Nullable |             Default
# -----------------+--------------------------+-----------+----------+----------------------------------
#  id              | integer                  |           | not null | generated always as identity
#  username        | character varying(255)   |           | not null |
#  hashed_password | character varying(255)   |           | not null |
#  created         | timestamp with time zone |           | not null |
#  updated         | timestamp with time zone |           | not null |
#  avatar_url      | text                     |           |          |    ← 追加された
```

---

## 12. リビジョンを進めたり戻したりする

Alembic では柔軟にリビジョンを移動できます：

```bash
# リビジョンを 1 つ前に戻す
uv run alembic downgrade -1

# リビジョンを 1 つ前に進める
uv run alembic upgrade +1

# 最初の状態（テーブルが何も無い状態）に戻す
uv run alembic downgrade base

# 最新のリビジョンに進める
uv run alembic upgrade head

# 特定のリビジョンに移動 (リビジョン ID を指定)
uv run alembic upgrade 634e50af5a67
uv run alembic downgrade da61d148b844
```

実際に何度か行ったり来たりしてみましょう。`\d users` の結果が変わるのが見えるはずです。

---

## 【発展】autogenerate が検出できる変更・できない変更

`alembic revision --autogenerate` は便利ですが、**全ての変更を検出できるわけではありません**。公式ドキュメントには [What does Autogenerate Detect (and what does it _not_ detect?)](https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect) として詳しい一覧があります。ここでは要点をまとめます。

### ✅ 確実に検出される変更

- **テーブルの追加・削除**
- **カラムの追加・削除**
- **カラムの NULL 許容性 (`nullable`) の変更**
- **インデックスの基本的な変更**
- **明示的に名前を付けられたユニーク制約 (`UniqueConstraint("...", name="...")` など) の追加・削除**
- **外部キー制約の基本的な変更**

### 🟡 オプションで検出される変更（デフォルト無効、env.py で有効化が必要）

- **カラム型の変更** … `compare_type=True` を `context.configure(...)` に渡すと有効化される。デフォルト値の `False` でも、メジャーな型差分や length・precision のような共通パラメータは比較される
- **カラムのサーバーデフォルト値 (`server_default`) の変更** … `compare_server_default=True` で有効化。シンプルなケースのみ動作するので、複雑な式の場合は callable で自前比較を書く

これらは初期値が控えめなので、本格運用する場合は env.py の `context.configure(...)` で有効化を検討する価値があります。

### ❌ 検出されない（または信頼できない）変更

- **テーブル名の変更 / カラム名の変更** … 「旧名前の削除 + 新名前の追加」と認識されるので、データが消えてしまいます。リネームは **手書きで `op.alter_column(..., new_column_name=...)` や `op.rename_table(...)`** に書き換えてからマイグレーションを適用すること
- **匿名で名前が付いている制約** … SQLAlchemy が自動命名した制約はリネームの対比ができず、変更検出が信頼できません。**制約には常に `name="..."` で明示的に名前を付ける**のが推奨
- **PostgreSQL の `ENUM` 型の値の追加・変更** … 新しい値を増やす場合は手書きで `op.execute("ALTER TYPE role_type ADD VALUE 'XXX'")` が必要
- **PRIMARY KEY / EXCLUDE / CHECK のような単独で立つ制約 や シーケンス操作** … 公式ドキュメントに「現状は対応していないが将来サポート予定」と記載されている領域
- **トリガー、ストアドプロシージャ、関数、ビュー、ポリシーなど** … 全般的に「テーブル定義の外側にあるオブジェクト」は検出対象外。今回 `set_updated_at` 関数とトリガーを手動追加したのはこの理由

> **教訓:** `alembic revision --autogenerate` で生成されたファイルは **必ず内容をレビュー** してから適用しましょう。意図しない変更（リネームのつもりが drop + add に化けている、など）が含まれていたり、必要な処理（トリガーの追加・修正など）が抜けていたりすることがあります。
>
> Chapter 4 の 9.1 で扱った **`alembic upgrade head --sql` で実行予定の SQL を確認する習慣** と組み合わせれば、autogenerate の出力が正しいかをさらに安全にチェックできます。

---

## まとめ

この章では以下を学びました：

- **マイグレーションが必要な理由**: 環境間のスキーマ同期、変更履歴の追跡、安全なロールバック
- **`pydantic-settings` で型付き設定** を作って Alembic とアプリで共有
- **Alembic のセットアップ**: `alembic init` → `env.py` でモデルと接続 URL を読み込む
- **autogenerate**: モデルと DB の差分から自動生成
- **トリガーは手書き**: autogenerate が検出できないので `op.execute()` で追加
- **シードデータ**: マイグレーションとは別の `seed.py` スクリプトとして実装。**冪等** に書くことで何度実行しても安全
- **マイグレーションの適用・戻し**: `alembic upgrade head` / `alembic downgrade ...`

これで `backend/app/` には `config.py` `session.py` `model.py` が揃い、DB スキーマは Alembic で管理されている状態になりました。次の章ではこれらを土台に、本格的な **CRUD API の実装** に入ります。

---

## 次の章

[Chapter 5: CRUD API の実装 →](../chapter05/README.md)
