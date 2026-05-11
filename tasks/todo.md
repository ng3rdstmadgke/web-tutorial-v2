# web-tutorial v2 計画

## ゴール

Web初心者がフルスタック開発を一通り体験できるチュートリアル。章ごとに `git tag` を切り、各章の末尾で「動くアプリ」を確認できる構成にする。

## 技術スタック

| 領域 | 採用技術 |
|---|---|
| バックエンド | FastAPI (Pydantic v2) + uv |
| フロントエンド | Next.js (App Router) + TypeScript |
| UIコンポーネント | shadcn/ui (Tailwind CSS ベース) |
| フォーム | React Hook Form + Zod |
| サーバー状態 | TanStack Query (Client Component で API を叩く章のみ) |
| DB | PostgreSQL |
| マイグレーション | Alembic |
| 型共有 | OpenAPI + openapi-typescript |
| テスト | pytest (API) / Playwright (E2E) |
| CI | GitHub Actions |
| デプロイ | Kubernetes (EKS 前提) |
| 認証 | 第1段階: 自前ID/PW + JWT in httpOnly Cookie<br>第2段階: Keycloak + 自前OIDC実装 |
| 開発環境 | Docker Compose |

## リポジトリ運用方式

- **1リポジトリを育てる方式**を採用。BE/FEは同一リポ内のサブディレクトリ（`backend/` / `frontend/`）。
- 各章ごとに `chapter{NN}-start` / `chapter{NN}-end` の git tag を打つ。
- 学習者はリポジトリをフォークし、`git checkout chapter05-start` のようにチェックアウトして作業開始。
- 各章 README に「スタート地点」と「答え合わせ用 compare URL」を記載。
- フレームワークのバージョンアップ時は main を直してタグを打ち直す（学習者は `git fetch --tags --force`）。

## ディレクトリ構成（最終形）

```
web-tutorial-v2/
├── README.md                  # チュートリアルのトップページ
├── CLAUDE.md
├── LICENSE                    # MIT
├── .gitignore
├── .editorconfig              # 任意
│
├── backend/                   # FastAPI（章を追うごとに育つ）
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version
│   ├── app/
│   ├── alembic/               # Chapter 4 で追加
│   └── tests/                 # Chapter 8 で追加
│
├── frontend/                  # Next.js（Chapter 10 で初登場）
│
├── e2e/                       # Playwright（Chapter 14 で初登場）
│
├── docker/                    # Dockerfile 群
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile    # Chapter 10 で追加
│   └── postgres/              # Chapter 3 で追加（必要なら）
│
├── compose.yaml               # ルート直下、章ごとに育つ
├── .env.example
│
├── k8s/                       # Chapter 16 で初登場（Kustomize: base + overlays）
│
├── .github/
│   └── workflows/             # Chapter 15 で初登場
│
├── docs/                      # 章ごとREADME
│   ├── README.md              # 全17章の目次
│   ├── chapter01/
│   │   ├── README.md
│   │   └── img/
│   └── ...
│
└── tasks/
    ├── todo.md
    └── lessons.md
```

### compose.yaml の段階的な育て方

| 章 | compose.yaml に追加されるもの |
|---|---|
| Chapter 1 | `backend` サービス（最小の FastAPI コンテナ、DB なし） |
| Chapter 3 | `db` サービス（PostgreSQL）追加、`backend` から接続 |
| Chapter 10 | `frontend` サービス（Next.js）追加 |
| Chapter 17 | `keycloak` サービス追加 |

### docs/ のREADMEテンプレ

各章の `docs/chapter{NN}/README.md` は以下の構造で統一：

```markdown
# Chapter N: タイトル

[← 目次に戻る](../README.md)

## この章のゴール
- 箇条書きで2〜4個

## スタート地点
git checkout chapter0N-start

## 完成形
git checkout chapter0N-end
差分: chapter0N-start...chapter0N-end の compare URL

## 前提知識
- 必要なら参考リンク

---

（本文）

---

## まとめ
- この章で学んだこと

## 学習チェックリスト
- 理解度確認の問い

## 次の章
[Chapter N+1: タイトル →](../chapter{N+1}/README.md)
```

## chapter01-start タグの中身

「Chapter 1 を始める前の状態」。`git checkout chapter01-start` した瞬間に Chapter 1 の手順を読みながら手を動かせる状態。

```
web-tutorial-v2/
├── README.md                  # チュートリアル全体のイントロ + docs/への誘導
├── CLAUDE.md
├── LICENSE                    # MIT
├── .gitignore                 # Python/Node/IDE 共通
├── .editorconfig              # 任意
├── docs/
│   ├── README.md              # 全17章の目次（リンクは順次有効化）
│   └── chapter01/
│       └── README.md          # Chapter 1 本文
└── tasks/
    ├── todo.md
    └── lessons.md
```

含めないもの：`backend/` `frontend/` `docker/` `compose.yaml` `k8s/` `.github/workflows/` `e2e/`（すべて該当章で作る）

## 章立て（確定版）

### 第1部: バックエンド基礎

- [x] **Chapter 1: 開発環境セットアップ (Docker Compose)**
  - **ゴール:** `docker compose up` で FastAPI が起動し、`http://localhost:8000` で Hello World が返る。コードを書き換えるとホットリロードする。
  - プロジェクト構成の説明
  - **uv とは / `pyproject.toml` / `uv.lock` の役割**
  - `backend.Dockerfile` を書く（uv でインストール、ホットリロード対応）
  - `compose.yaml` を書く（**backend サービスのみ、DB はまだ立てない**）
  - `docker compose up` で起動確認
  - **補足コラム:** VS Code ユーザー向けの devcontainer の話（本筋はターミナル/任意エディタから動く構成）
  - ※ FastAPI 本体は写経で最小ファイル（Hello World）を置くだけ。ルーティング・Pydantic・OpenAPI の解説は Chapter 2 に集約。

- [x] **Chapter 2: FastAPI入門**
  - ルーティング、パスパラメータ、クエリ、リクエストボディ
  - Pydantic v2 によるバリデーション
  - 自動生成される OpenAPI / Swagger UI を確認

- [x] **Chapter 3: PostgreSQL + SQLAlchemy**
  - **`compose.yaml` に `db` サービス（PostgreSQL）を追加**
  - 生SQL で基本操作 → SQLAlchemy 2.x スタイル（`Mapped[...]`, `session.execute(select(...))`）
  - セッション管理の考え方

- [x] **Chapter 4: Alembic によるマイグレーション**
  - モデル変更 → リビジョン生成 → apply の流れ
  - なぜ手動 ALTER ではダメか

- [x] **Chapter 5: CRUD API の実装**
  - User/Item の CRUD
  - ルーター分割、依存性注入（`Depends`）、レイヤ分離

- [x] **Chapter 6: 認証・認可（自前ID/PW）**
  - パスワードハッシュ（argon2）
  - JWT 発行・検証
  - **httpOnly Cookie でトークンを保持**（XSS耐性、CSRF対策含めて解説）
  - ロールベースの認可

- [x] **Chapter 7: 構造化ログとエラーハンドリング**
  - 例外ハンドラ、エラーレスポンス設計
  - structlog による JSON ログ
  - リクエストID の付与

- [ ] **Chapter 8: APIテスト (pytest)**
  - fixture でテスト用DB/ユーザーをセットアップ
  - 認証が必要なエンドポイントのテスト

### 第2部: フロントエンド

- [ ] **Chapter 9: JS/TS おさらい (外部リンク集)**
  - サバイバルTypeScript、公式Tutorial などへのリンク
  - 本編に最低限必要な概念だけ簡潔にまとめる

- [ ] **Chapter 10: Next.js 入門 + Tailwind CSS 基礎**
  - **`compose.yaml` に `frontend` サービスを追加**
  - App Router の基本（Server Component / Client Component）
  - ルーティング、レイアウト
  - **Tailwind CSS の基本**（ユーティリティ、レスポンシブ、`hover:`/`focus:` バリアント、`@apply`）
  - shadcn/ui のセットアップと使い方
  - Tailwind を素で書く場面と shadcn/ui を使う場面の使い分け

- [ ] **Chapter 11: OpenAPI駆動の型生成**
  - `openapi-typescript` で FastAPI の OpenAPI から TS 型生成
  - 型付き fetch クライアントの使い方
  - CI で型の追従チェック

- [ ] **Chapter 12: ログインページの実装**
  - Chapter 6 のID/PW認証と接続（httpOnly Cookie）
  - **React Hook Form + Zod** を導入してフォーム/バリデーションを実装
  - shadcn/ui の `<Form>` コンポーネント活用
  - 認証ガード（middleware で Cookie を見て未ログインならリダイレクト）

- [ ] **Chapter 13: CRUD画面の実装**
  - アイテム管理・ユーザー管理画面
  - Server Component で初期データ取得 / Client Component で更新系
  - **TanStack Query を Client Component の API 呼び出しで導入**（一覧の自動再検証、楽観的更新）
  - サーバー側 fetch とクライアント側 fetch の使い分け方針

- [ ] **Chapter 14: E2Eテスト (Playwright)**
  - ログイン〜CRUD操作のシナリオ
  - CI での実行

### 第3部: 運用・公開

- [ ] **Chapter 15: GitHub Actions で CI**
  - バックエンド（lint/test）、フロント（lint/type-check/test）、E2E を統合
  - PR チェックのフロー

- [ ] **Chapter 16: k8s (EKS) へのデプロイ**
  - Kustomize 構造（base + overlays）でマニフェスト記述
  - Ingress / Service / Deployment の役割
  - シークレット管理
  - イメージのビルド〜プッシュ〜デプロイの流れ

### 第4部: 発展

- [ ] **Chapter 17: Keycloak + 自前OIDC実装**
  - **`compose.yaml` に `keycloak` サービスを追加**
  - Keycloak で realm/client を作る
  - OIDC Authorization Code Flow + PKCE を自前実装で理解する
  - Chapter 6 の自前認証をリプレイス
  - 「なぜライブラリに頼らず書くのか」＝プロトコル理解のため

- [ ] **Chapter 18: 画像アップロード機能 (構想)**
  - Chapter 4 で `users.avatar_url` カラムを追加するが、本章までは外部 URL を貼る前提で運用
  - 本章で **アプリケーションからの画像アップロード・配信** を本格実装
  - 検討事項:
    - 保存先: ローカルファイルシステム (`backend/uploads/`) / S3 互換 (MinIO) / DB BLOB のいずれか
    - 配信: FastAPI `StaticFiles` / 署名付き URL / Next.js 経由
    - バリデーション: ファイルサイズ・MIME タイプ・拡張子チェック
    - 画像のリサイズ・サムネイル生成（Pillow など）
    - k8s デプロイ時のストレージ戦略（PV か外部オブジェクトストレージか）

## 次のステップ

1. 既存の不要ディレクトリを削除（`docker/`, `k8s/`, `terraform/`, `sample-app/`, `bin/`, `docs/`, `.devcontainer/` のうち雛形由来のもの）
2. `chapter01-start` 相当のファイルを作る（README, LICENSE, .gitignore, docs/README.md, docs/chapter01/README.md, tasks/lessons.md）
3. `chapter01-start` タグを打つ
4. Chapter 1 の実装に入る（backend/, docker/backend.Dockerfile, compose.yaml）
5. 完了したら `chapter01-end` タグを打つ

## レビューセクション

（各章の実装完了時に追記）
