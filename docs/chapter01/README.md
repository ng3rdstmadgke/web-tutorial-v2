# Chapter 1: 開発環境セットアップ (Docker Compose)

[← 目次に戻る](../README.md)

## この章のゴール

- Docker Compose で **FastAPI コンテナ** を起動できる
- ブラウザで `http://localhost:8000` を開くと "Hello World" が返ってくる
- ソースコードを書き換えると **ホットリロード** で自動反映される

> **この章で扱うのは「環境構築」だけです。** FastAPI のルーティングや Pydantic などのコードの書き方は Chapter 2 で学びます。

## スタート地点

```bash
git checkout chapter01-start
```

## 完成形

```bash
git checkout chapter01-end
```

---

## はじめに

このチュートリアルでは **必ず Dev Container 上で作業** します。Dev Container を使うことで、学習者ごとに OS や言語のバージョンが違うことによる「動かない」問題を避けられます。

このリポジトリには既に `.devcontainer/` が用意されており、以下のツールがインストール済みです：

| ツール | 用途 |
|---|---|
| `docker` (outside-of-docker) | コンテナ操作 |
| `uv` | Python のパッケージマネージャ |
| `node`, `npm`, `pnpm` | Node.js（後の章で使う） |
| `psql` | PostgreSQL クライアント（Chapter 3 以降で使う） |
| `kubectl`, `helm`, `k9s` | Kubernetes 系（Chapter 16 で使う） |

つまり **Dev Container を起動した時点で、学習に必要なツールは全部入っている** ことになります。

### Dev Container を起動する

1. このリポジトリを **フォーク** してローカルにクローン
2. VS Code でリポジトリを開く
3. コマンドパレット (`F1`) → **「Dev Containers: Reopen in Container」** を選択
4. 初回はビルドに数分かかる
5. ターミナルが Dev Container 内のシェルになっていれば成功

以降、すべてのコマンドは **Dev Container のターミナル内で実行** します。

---

## この章で作るファイル

```
web-tutorial-v2/
├── backend/                 # ← 今回新規作成
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version
│   └── app/
│       └── main.py
├── docker/                  # ← 今回新規作成
│   └── backend.Dockerfile
└── compose.yaml             # ← 今回新規作成
```

---

## 1. uv とは

[uv](https://docs.astral.sh/uv/) は Rust 製の **Python パッケージマネージャ** です。`pip` や `poetry` の役割を高速に置き換えるツールで、近年の FastAPI プロジェクトで広く採用されています。

### `pyproject.toml` と `uv.lock` の役割

- **`pyproject.toml`** … 依存パッケージの **要件**（"FastAPI 0.115 以上が必要" など）を記述する
- **`uv.lock`** … 実際にインストールされる **正確なバージョン** を全パッケージ分記録するロックファイル

`pyproject.toml` だけだと「FastAPI 0.115 以上」という曖昧さが残るため、別環境で `uv sync` したときに違うバージョンが入る可能性があります。`uv.lock` を git にコミットしておけば、誰がいつどこで `uv sync` しても **完全に同じバージョン** がインストールされます。

### Python のプロジェクトを作る

Dev Container のターミナルで以下を実行します：

```bash
# プロジェクトルートで作業
cd /workspaces/web-tutorial-v2

# backend ディレクトリを作って Python プロジェクトを初期化
uv init backend --bare --python 3.12
cd backend

# FastAPI を依存に追加 (--extra standard で Uvicorn など標準ツール一式も同時にインストール)
uv add fastapi --extra standard
```

実行後、以下のファイルが生成されます：

- `backend/pyproject.toml` … FastAPI が `[project.dependencies]` に追加されている
- `backend/uv.lock` … 解決された全バージョンが記録されている
- `backend/.python-version` … Python 3.12 を指定

> **`uv init` の `--bare` オプション** は「`main.py` や `README.md` などのサンプルファイルを生成せず、`pyproject.toml` だけを作る」という意味です。今回は自前で `app/main.py` を書くので、サンプルは不要です。
>
> **`--extra standard` オプション** は FastAPI のオプション機能をまとめてインストールするための指定で、Uvicorn (ASGI サーバ)、HTTPX、ファイル監視ツールなど標準的に使うパッケージが一括で入ります。これは `uv add 'fastapi[standard]'` と同じ意味です。

---

## 2. FastAPI の最小コードを書く

`backend/app/` ディレクトリを作り、`main.py` を以下の内容で作成します：

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

```dockerfile
# docker/backend.Dockerfile
FROM python:3.12-slim

# uv をコンテナにインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 作業ディレクトリ
WORKDIR /workspace

# 依存定義をコピーして先にインストール (Docker のレイヤーキャッシュを活かす)
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-install-project

# アプリのソースコードをコピー
COPY backend/app ./app

# Uvicorn を起動 (--reload で自動リロード)
CMD ["uv", "run", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### ポイント解説

- **`FROM python:3.12-slim`** … 軽量な Python 3.12 公式イメージを使用
- **`COPY --from=ghcr.io/astral-sh/uv:latest`** … uv の公式イメージから `uv` バイナリだけを取り出す方式（公式推奨）
- **`uv sync --locked --no-install-project`** … `uv.lock` が `pyproject.toml` と整合していることを検証した上で、依存パッケージだけを先にインストールする。`--no-install-project` を付けることでアプリ自身のコード（`app/`）はインストールしない。アプリのソースは別レイヤーにコピーすることで、ソース変更時に依存の再インストールが走らないようにしている
- **`--reload`** … ファイル変更を検知して Uvicorn が自動再起動する開発用フラグ

---

## 4. compose.yaml を書く

プロジェクトルートに `compose.yaml` を作成します：

```yaml
# compose.yaml
services:
  backend:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    ports:
      - "8000:8000"
    volumes:
      # ホスト側のソースをコンテナにマウント (ホットリロード用)
      - ./backend/app:/workspace/app
```

### ポイント解説

- **`build.context: .`** … プロジェクトルートをビルドコンテキストにする。これにより Dockerfile から `backend/` も `docker/` も両方参照できる
- **`ports: "8000:8000"`** … コンテナの 8000 番ポートをホストの 8000 番にバインド。ホストブラウザから `http://localhost:8000` で接続できる
- **`volumes`** … `backend/app` をコンテナにマウントすることで、ホスト側でコードを編集すると即座にコンテナにも反映される（`--reload` と組み合わせてホットリロード実現）

> **なぜルート直下に `compose.yaml` を置くのか？**
> Docker Compose v2 では `docker compose up` を引数なしで叩くと、カレントディレクトリの `compose.yaml` を自動で読みます。プロジェクトルートに置くことで、どこから起動しても迷いません。

---

## 5. 起動して動作確認

Dev Container のターミナルで以下を実行：

```bash
# プロジェクトルートで実行
cd /workspaces/web-tutorial-v2

# ビルドして起動 (-d でバックグラウンド)
docker compose up -d --build

# 起動状態を確認
docker compose ps
```

`STATUS` が `Up` になっていれば起動成功です。

### Hello World を確認

```bash
curl http://localhost:8000
# => {"message":"Hello World"}
```

ホスト側のブラウザで `http://localhost:8000` を開いても同じ JSON が表示されます。

### Swagger UI も確認

FastAPI は **OpenAPI ドキュメントを自動生成** します。`http://localhost:8000/docs` を開いてみてください。`GET /` のエンドポイントが一覧に表示され、ブラウザから直接 API を実行できます。これだけでも FastAPI の便利さの一端が見えます。

### ホットリロードを試す

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

再度 `curl http://localhost:8000` で確認すると、メッセージが `"Hello FastAPI"` に変わっています。**コンテナを再起動せずに変更が反映される** のがホットリロードです。

### 停止する

```bash
docker compose down
```

---

## まとめ

この章では以下を学びました：

- Dev Container を使えば、学習に必要なツールが揃った環境にすぐ入れる
- **uv** は高速な Python パッケージマネージャで、`pyproject.toml` と `uv.lock` で依存を管理する
- Dockerfile で uv 公式イメージから `uv` バイナリをコピーする手法
- Docker Compose の `volumes` と Uvicorn の `--reload` を組み合わせて **ホットリロード** を実現する
- FastAPI は **`/docs` で OpenAPI ドキュメントを自動生成** する

## 学習チェックリスト

以下の問いに自分の言葉で答えられるか確認してみましょう：

- [ ] `pyproject.toml` と `uv.lock` の違いは？ なぜ両方が必要なのか？
- [ ] Dockerfile で「依存をインストール → ソースをコピー」の順にする理由は？
- [ ] `volumes` でマウントしているのに、ホットリロードが動かない場合に最初に疑うところは？
- [ ] `docker compose up` と `docker compose up -d` の違いは？

## 次の章

[Chapter 2: FastAPI 入門 →](../chapter02/README.md)
（公開され次第リンクが有効になります）
