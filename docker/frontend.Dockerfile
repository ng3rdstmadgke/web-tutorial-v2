FROM node:22-bookworm-slim

# CI 環境とみなしてもらい、TTY が必要な対話プロンプトをスキップする
ENV CI=true

# corepack を有効化して pnpm を使えるようにする (マイナーまで固定、patch は最新を許容)
RUN corepack enable && corepack prepare pnpm@11.1 --activate

WORKDIR /opt/frontend

# 依存定義をコピーしてインストール (pnpm-workspace.yaml には allowBuilds の設定が入っている)
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# アプリのソースをコピー
COPY frontend ./

EXPOSE 3000

# 開発サーバーを起動（コンテナ外からアクセスできるよう 0.0.0.0 で待ち受け）
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]