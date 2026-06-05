# ===== base: dev / prod 共通。uv と依存定義をそろえる =====
FROM python:3.14-slim AS base

# uv をコンテナにインストール（バージョン固定）
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

WORKDIR /opt/backend

# 依存定義をコピー（レイヤキャッシュを効かせるため先にコピーする）
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./

# ===== dev: ホットリロード対応（compose.yaml が target: dev で使用）=====
FROM base AS dev
RUN uv sync --locked --no-install-project
COPY backend/app /opt/backend/app
COPY backend/alembic /opt/backend/alembic
COPY backend/alembic.ini /opt/backend/alembic.ini
CMD ["uv", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

# ===== prod: 本番用。dev 依存を除き、reload なしで起動 =====
FROM base AS prod
# 本番依存のみインストール（pytest / ruff / mypy / jupyter を含めない）
RUN uv sync --locked --no-install-project --no-dev
COPY backend/app /opt/backend/app
COPY backend/alembic /opt/backend/alembic
COPY backend/alembic.ini /opt/backend/alembic.ini
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]