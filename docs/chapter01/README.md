# Chapter 1: 開発環境セットアップ (Docker Compose)

[<- 目次に戻る](../../README.md)

## この章のゴール

- Docker Compose で **FastAPI コンテナ** を起動できる
- ブラウザで `http://localhost:8000` を開くと "Hello World" が返ってくる
- ソースコードを書き換えると **ホットリロード** で自動反映される

> [!NOTE] この章で扱うのは「環境構築」だけです。
> FastAPI のルーティングや Pydantic などのコードの書き方は Chapter 2 で学びます。

## スタート地点

```bash
# チュートリアルの開始地点
git checkout chapter01-start
```

## 完成形

```bash
git checkout chapter02-start
```

---

## はじめに

このチュートリアルは VSCode の **Dev Container** 機能を利用することを想定しています。  
Dev Container を使うことで、学習者ごとに OS や言語のバージョンが違うことによる「動かない」避ける意図です。

> [!NOTE] このチュートリアルはUbuntu24.04で動作検証しています。


### 前準備

- 公式のインストール手順に従ってDockerをインストールしてください  
  [Install Docker Engine | Docker](https://docs.docker.com/engine/install/)
- 必要なパッケージのインストール  
  `sudo apt update && sudo apt install -y git

### リポジトリを準備する (private 複製)

このチュートリアルは自身のGitHubアカウントにこのリポジトリのコピーして作業することを推奨しています。  

> [!NOTE] forkではなくコピー
> 本チュートリアルはChapter14以降にGitHub ActionsによるCI/CDを行います。その時にプライベートリポジトリとしたいため、以下の手順でリポジトリをコピーしてください。  
> forkだと、プライベートリポジトリにできません。


#### 1. プライベートリポジトリの作成
[Create a new repository | GitHub](https://github.com/new) から `web-tutorial-v2` という名前でプライベートリポジトリを作成して、リポジトリのURLを控えておいてください。


#### 2. リポジトリのコピー

```bash
# ローカルにプライベートリポジトリをコピー
git clone https://github.com/ng3rdstmadgke/web-tutorial-v2.git

cd web-tutorial-v2

# リモートURLを咲穂自身のGitHubに作成したプライベートリポジトリのURLに書き換え
git remote set-url origin https://github.com/xxxxxxxxxxxxxxx/web-tutorial-v2.git

# 自身のプライベートリポジトリにソースコードをpush
git push origin main
# タグもpush
git push origin --tags
```

### Dev Container を起動する

1. 複製手順で用意したローカルのリポジトリ (`web-tutorial-v2`) を VS Code で開く
1. コマンドパレット (`F1`) -> **「Dev Containers: Reopen in Container」** を選択
1. 初回はビルドに数分かかる
1. ターミナルが Dev Container 内のシェルになっていれば成功

以降、すべてのコマンドは **Dev Container のターミナル内で実行** します。

### このチュートリアルで使う環境変数

Dev Container 内には予めよく利用する環境変数が定義されています。環境変数の定義は `.devcontainer/devcontainer.json` `.devcontainer/.env` で行われます

代表的な環境変数:
- `$PROJECT_DIR` : Dev Container 内のプロジェクトルートの絶対パス (`/workspaces/web-tutorial-v2`)
- `$HOST_DIR` : ホストOS上のプロジェクトルートの絶対パス (`/home/your-name/web-tutorial-v2`)
- `$HOST_USER` : ホストOS上のユーザー名


---

## この章で作るファイル

```
web-tutorial-v2/
├── backend/                 # <- 今回新規作成
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version
│   └── app/
│       └── main.py
├── docker/                  # <- 今回新規作成
│   └── backend.Dockerfile
├── compose.yaml             # <- 今回新規作成
└── .dockerignore            # <- 今回新規作成
```

---

## 1. uv とは

[uv](https://docs.astral.sh/uv/) は Rust 製の Python パッケージマネージャです。`pip` や `poetry` の役割を高速に置き換えるツールで、近年の Python プロジェクトで広く採用されています。

### `pyproject.toml` と `uv.lock` の役割

- **`pyproject.toml`** … 依存パッケージの **要件**("FastAPI 0.115 以上が必要" など)を記述する
- **`uv.lock`** … 実際にインストールされる **正確なバージョン** を全パッケージ分記録するロックファイル

`pyproject.toml` だけだと「FastAPI 0.115 以上」という曖昧さが残るため、別環境で `uv sync` したときに違うバージョンが入る可能性があります。`uv.lock` を git にコミットしておけば、誰がいつどこで `uv sync` しても **完全に同じバージョン** がインストールされます。

### Python のプロジェクトを作る

Dev Container のターミナルで以下を実行します：

```bash
# プロジェクトルートで作業
cd $PROJECT_DIR

# ゴミが残ってしまっている可能性があるので削除
sudo rm -rf $PROJECT_DIR/backend

# backend ディレクトリを作って Python プロジェクトを初期化
uv init backend --bare --python 3.12
cd $PROJECT_DIR/backend

# .python-versionファイル生成してPythonのバージョンを3.12に固定
uv python pin 3.12

# FastAPI を依存に追加 (--extra standard で Uvicorn など標準ツール一式も同時にインストール)
uv add fastapi~=0.136.1 --extra standard
```

実行後、以下のファイルが生成されます：

- `backend/pyproject.toml` … FastAPI が `[project.dependencies]` に追加されている
- `backend/uv.lock` … 解決された全バージョンが記録されている
- `backend/.python-version` … Python 3.12 を指定

> [!NOTE] `uv init` の `--bare` オプション
> `main.py` や `README.md` などのサンプルファイルを生成せず、`pyproject.toml` だけを生成します。

> [!NOTE] `--extra standard` オプション
> FastAPI のオプション機能をまとめてインストールするための指定で、Uvicornなどの標準的に使うパッケージが一括で入ります。(`uv add 'fastapi[standard]'` と同義)

---

## 2. FastAPI の最小コードを書く

`backend/app/` ディレクトリを作り、`main.py` を以下の内容で作成します：

```bash
mkdir -p $PROJECT_DIR/backend/app
touch $PROJECT_DIR/backend/app/main.py
```

```python
# backend/app/main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello World"}
```

たった 7 行のコードですが、これで「`/` にアクセスすると JSON で `{"message": "Hello World"}` を返す Web API」が完成しています。FastAPI の詳しい話は Chapter 2 で扱うので、今は「こういう書き方なんだ」程度で大丈夫です。

---

## 3. Dockerfile を書く

`docker/backend.Dockerfile` を以下の内容で作成します：

```bash
mkdir -p $PROJECT_DIR/docker
touch $PROJECT_DIR/docker/backend.Dockerfile
```

```dockerfile
# docker/backend.Dockerfile
FROM python:3.12-slim

# uv の公式イメージから uv バイナリだけを取り出す
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

# 作業ディレクトリ
WORKDIR /opt/backend

# 依存定義をコピーして先にインストール
# --locked: uv.lock が pyproject.toml と整合していることを検証
# --no-install-project: アプリ自身のコード (app/) はまだインストールせず、
#                       ソース変更時に依存の再インストールが走らないようにする
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-install-project

# アプリのソースコードをコピー
COPY backend/app /opt/backend/app

# Uvicorn を起動。 --reload はファイル変更を検知して自動再起動する開発用フラグ
CMD ["uv", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
```

> [!TIP] 公式ドキュメント:
> - [Using uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/#installing-uv)

---

## 4. compose.yaml を書く

プロジェクトルートに `compose.yaml` を作成します：

```bash
touch $PROJECT_DIR/compose.yaml
```

```yaml
# compose.yaml
name: web-tutorial-v2-${HOST_USER}

services:
  backend:
    container_name: web-tutorial-v2-backend-${HOST_USER}
    build:
      # プロジェクトルートをビルドコンテキストにする (Dockerfile から backend/ も docker/ も両方参照できる)
      context: .
      dockerfile: docker/backend.Dockerfile
    volumes:
      # ホスト側のソースをマウントすることで、 ホスト側の編集が即コンテナに反映される
      # (Dockerfile の --reload と組み合わせてホットリロード実現)
      - ${HOST_DIR}/backend/app:/opt/backend/app  # ホスト側:コンテナ側
    networks:
      # devcontainerと同じネットワークで起動
      - devcontainer-nw
networks:
  devcontainer-nw:
    external: true
    name: br-web-tutorial-v2-${HOST_USER}
```

---

## 5.dockerignore でビルドコンテキストを絞る

`build` の `context: .`(リポジトリ直下)には、`.env` などの秘密情報や、ホストの依存・ビルド生成物・キャッシュも含まれます。これらは **イメージに不要なうえ、ビルドのたびに Docker へ転送されてビルドを遅くします**。リポジトリ直下に `.dockerignore` を作り、ビルドコンテキストから除外します。

```bash
touch $PROJECT_DIR/.dockerignore
```

```gitignore
# .dockerignore

# 環境変数ファイル(実行時に注入するためイメージには含めない)
**/.env
**/.env.*

# 依存・ビルド生成物(イメージ内で生成し直す。ホストのものは持ち込まない)
**/node_modules
**/.next
**/.venv
**/__pycache__
**/*.pyc

# 各種キャッシュ
**/.pytest_cache
**/.ruff_cache
**/.mypy_cache

# バージョン管理・ツール
.git
.gitignore
.devcontainer

# イメージのビルドに不要なもの
docs
agent-tasks
e2e
tmp
```

> [!NOTE] ポイント解説:
> `.dockerignore` に書いたパスは Docker がビルドコンテキストへ送る対象から外れます。`.env` のような秘密情報や、`node_modules` などホスト環境固有のものをイメージに持ち込まずに済み、ビルドも速くなります。`.gitignore` と書式は同じですが、対象は **Docker のビルドコンテキスト** です。

---

## 6. 起動して動作確認

Dev Container のターミナルで以下を実行：

```bash
# プロジェクトルートで実行
cd $PROJECT_DIR

# 既存コンテナを破棄して、最新の設定でビルドしてバックグラウンド起動
docker compose down && docker compose up -d --build

# 起動状態を確認
docker compose ps
# NAME                              IMAGE                     COMMAND                  SERVICE   CREATED         STATUS         PORTS
# web-tutorial-v2-backend-ktamido   web-tutorial-v2-backend   "uv run uvicorn app.…"   backend   7 minutes ago   Up 7 minutes   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tc
```

`STATUS` が `Up` になっていれば起動成功です。

### Hello World を確認

#### Dev Container 内のターミナルから

Dev Container と FastAPI コンテナは **同じ Docker ネットワーク** に所属しているので、サービス名で直接アクセスできます。

```bash
curl http://backend:8000
# {"message":"Hello World"}
```

#### ローカル環境のブラウザから

`.devcontainer/devcontainer.json` の `forwardPorts` で `backend:8000` をフォワーディングしているので、ローカル環境のブラウザから `http://localhost:8000` でアクセスできます。

<img src="img/fastapi_01.png" width="700px">

#### 補足: ネットワーク構成

ここで「なぜ `localhost` でも動いて、サービス名でも動くのか？」を整理しておきます。Dev Container と FastAPI コンテナは、ホスト OS 上で動く **同じ Docker bridge ネットワーク** に接続されています。

```
    ローカル環境の 8000 番ポートへフォワーディング
              ▲
              │
┌─ Host OS ───┼──────────────────────────────────────────────────────┐
│             │                                                      │
│    ┌─────────────────┐                ┌─────────────────────────┐  │
│    │ Dev Container   │                │ FastAPI Container       │  │
│    │                 │                │ (backend:8000)          │  │
│    │                 │                │                         │  │
│    │                 │                │                         │  │
│    └────────┬────────┘                └────────────┬────────────┘  │
│             │                                      │               │
│             │                                      │               │
│             └──────────────────┬───────────────────┘               │
│                                │                                   │
│              ┌─────────────────┴─────────────────┐                 │
│              │ Docker bridge network             │                 │
│              │ br-web-tutorial-v2-${HOST_USER}   │                 │
│              └───────────────────────────────────┘                 │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

- Dev Container は `.devcontainer/devcontainer.json` の `runArgs` の指定で `br-web-tutorial-v2-${localEnv:USER}` ネットワークに参加しています
- FastAPI コンテナも同じく `compose.yaml` の `nwtworks` の指定で `br-web-tutorial-v2-${HOST_USER}` ネットワークに参加しています
- 同一ネットワーク内では **compose のサービス名** が DNS で解決されるため、Dev Container から `backend` という名前で FastAPI コンテナに到達できます。

| アクセス元 | 使えるアドレス | 仕組み |
|---|---|---|
| ローカル環境のブラウザ | `http://localhost:8000` | `.devcontainer/devcontainer.json` の `forwardPorts` でローカル環境に転送している |
| Dev Container のターミナル | `http://backend:8000` | 同じ Docker ネットワーク内なので **サービス名** `backend` で名前解決できる |

### Swagger UI も確認

FastAPI は **OpenAPI ドキュメントを自動生成** します。`http://localhost:8000/docs` を開いてみてください。  
`GET /` のエンドポイントが一覧に表示され、ブラウザから直接 API を実行できます。

<img src="img/swagger_ui_01.png" width="700px">

<img src="img/swagger_ui_02.png" width="700px">

### ホットリロードを試す

`backend` コンテナはローカルのソースコードを参照して、ホットリロード設定が有効化されているため、ソースコードを書き換えると、コンテナの再起動なしに変更が適用されます。ソースコードを修正して、変更が適用されるかを確認します。


> [!NOTE] ローカルソースコードの参照
> `compose.yaml` の `services.backend.volumes` の以下の設定で、コンテナの `/opt/backend/app` にローカルの `backend/app` をマウントしています。
>
> ```yaml
> - ${HOST_DIR}/backend/app:/opt/backend/app  # ホスト側:コンテナ側
> ```

> [!NOTE] ホットリロード設定
> `docker/backend.Dockerfile` の `CMD` (起動コマンド設定) に `--reload` オプションを指定することで、ソースコードの修正が自動で適用される開発モードとなります。
>
> ```Dockerfile
> CMD ["uv", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
> ```

`backend/app/main.py` を以下のように書き換えて保存します：

```python
@app.get("/")
def read_root():
    return {"message": "Hello FastAPI"}
```

すると Dev Container のターミナルで以下のようなログが流れるはずです：

```
WARNING:  WatchFiles detected changes in 'app/main.py'. Reloading...
```

再度 `curl http://localhost:8000` で確認すると、メッセージが `"Hello FastAPI"` に変わっています。

```bash
curl http://backend:8000
# {"message":"Hello FastAPI"}
```

### 停止する

`docker compose up` をフォアグラウンドで実行している場合、ターミナルで `Ctrl+C` を押してプロセスに停止シグナルを送ります。これでコンテナの **動作** が止まります。  
ただし `Ctrl+C` だけだと **コンテナ自体は停止状態で残った** ままです。コンテナを完全に削除したい場合は以下を実行します。

```bash
# プロジェクトルートで実行
cd $PROJECT_DIR

# コンテナとネットワークを停止・削除する
docker compose down
```

| コマンド | 効果 |
|---|---|
| `Ctrl+C` | フォアグラウンド実行中のコンテナを停止する(コンテナは残る) |
| `docker compose stop` | バックグラウンド実行中のコンテナを停止する(コンテナは残る) |
| `docker compose down` | コンテナを停止して **削除** する(compose で作ったネットワークも削除) |

---

## 次の章

[Chapter 2: FastAPI 入門 ->](../chapter02/README.md)
