# Web アプリ作成チュートリアル v2

バックエンドに **FastAPI** (Python)、フロントエンドに **Next.js** (TypeScript)、データベースに **PostgreSQL** を利用した、モダンな Web アプリのチュートリアルです。

章ごとに段階的にアプリを育てていく構成になっており、各章末で「動くアプリ」を確認できます。

## 対象読者

- これから Web アプリ開発を始めたい方
- フロントエンドからバックエンド、デプロイまでフルスタックで一通り触ってみたい方

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

## 進め方

このリポジトリは **1 つのリポジトリを章ごとに育てていく** 方式です。各章には `chapter{NN}-start` / `chapter{NN}-end` の git tag が打たれているので、好きな章から始められます。

```bash
# このリポジトリをフォーク・クローンしたあと
git fetch --tags

# Chapter 1 の開始地点に移動
git checkout chapter01-start

# 学習を進める。詰まったら答えを見たい場合は完成形に切り替え
git checkout chapter01-end
```

### 必要な環境

- **Docker** (Docker Desktop または Docker Engine)
- **VS Code** + **Dev Containers 拡張**

学習者は **必ず Dev Container 上で作業する** 前提です。ホスト OS には Docker と VS Code さえ入っていれば、その他のツール（Python、Node.js、uv など）は Dev Container がすべて用意します。

## 目次

[**docs/README.md**](docs/README.md) を参照してください。

## ライセンス

[MIT License](LICENSE)
