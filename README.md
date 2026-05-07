# Web アプリ作成チュートリアル v2

バックエンドに **FastAPI** (Python)、フロントエンドに **Next.js** (TypeScript)、データベースに **PostgreSQL** を利用した、モダンな Web アプリのチュートリアルです。

章ごとに段階的にアプリを育てていく構成になっており、各章末で「動くアプリ」を確認できます。

## 技術スタック

| 領域 | 採用技術 |
|---|---|
| バックエンド | FastAPI (Pydantic v2) + uv |
| フロントエンド | Next.js (App Router) + TypeScript |
| UI コンポーネント | shadcn/ui (Tailwind CSS) |
| DB | PostgreSQL |
| マイグレーション | Alembic |
| テスト | pytest / Playwright |
| CI | GitHub Actions |
| デプロイ | Kubernetes (EKS) |
| 認証 | 自前 ID/PW + JWT → Keycloak + 自前 OIDC |
| 開発環境 | Docker Compose + VS Code Dev Container |

## 目次

### 第1部: バックエンド基礎

- [Chapter 1: 開発環境セットアップ (Docker Compose)](docs/chapter01/README.md)
- [Chapter 2: FastAPI 入門](docs/chapter02/README.md)
- [Chapter 3: PostgreSQL + SQLAlchemy](docs/chapter03/README.md)
- [Chapter 4: Alembic によるマイグレーション](docs/chapter04/README.md)
- [Chapter 5: CRUD API の実装](docs/chapter05/README.md)
- [Chapter 6: 認証・認可(自前 ID/PW)](docs/chapter06/README.md)
- [Chapter 7: 構造化ログとエラーハンドリング](docs/chapter07/README.md)
- [Chapter 8: API テスト (pytest)](docs/chapter08/README.md)

### 第2部: フロントエンド

- [Chapter 9: JS/TS おさらい (外部リンク集)](docs/chapter09/README.md)
- [Chapter 10: Next.js 入門 + Tailwind CSS 基礎](docs/chapter10/README.md)
- [Chapter 11: OpenAPI 駆動の型生成 + ログインページの実装](docs/chapter11/README.md)
- [Chapter 12: CRUD 画面の実装](docs/chapter12/README.md)
- [Chapter 13: E2E テスト (Playwright)](docs/chapter13/README.md)

### 第3部: 運用・公開

- [Chapter 14: GitHub Actions で CI](docs/chapter14/README.md)
- [Chapter 15: k8s (EKS) へのデプロイ](docs/chapter15/README.md)

### 第4部: 発展

- Chapter 16: Keycloak + 自前 OIDC 実装

### Appendix

- [Appendix](docs/appendix/README.md)

 


## ライセンス

[MIT License](LICENSE)
