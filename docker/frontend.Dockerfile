# ===== base: dev / build 共通。依存をインストールする =====
FROM node:22-bookworm-slim AS base
ENV CI=true
# corepack を有効化（pnpm のバージョンは package.json の "packageManager" に従う）
RUN corepack enable
WORKDIR /opt/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# ===== dev: 開発サーバー（compose.yaml が target: dev で使用）=====
FROM base AS dev
COPY frontend ./
EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]

# ===== build: 本番ビルド。.next/standalone を出力する =====
FROM base AS build
COPY frontend ./
# next build はサーバー側モジュール評価で env.INTERNAL_API_URL を参照・検証する。
# 実値は実行時に注入するため、ビルドを通すためのダミー値を渡す（実行時の環境変数で上書きされる）。
ENV INTERNAL_API_URL=http://localhost:8000
RUN pnpm build

# ===== prod: standalone を node で起動する最小ランタイム =====
FROM node:22-bookworm-slim AS prod
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
WORKDIR /opt/frontend
# standalone 本体 + 静的アセット + public を配置（server.js がこれらを配信する）
COPY --from=build /opt/frontend/.next/standalone ./
COPY --from=build /opt/frontend/.next/static ./.next/static
COPY --from=build /opt/frontend/public ./public
EXPOSE 3000
CMD ["node", "server.js"]