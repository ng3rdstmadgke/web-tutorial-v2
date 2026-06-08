from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging
from app.middleware import RequestLoggingMiddleware
from app.routers import router
from app.session import get_session

# ログ設定（最初に呼ぶ）
setup_logging()

app = FastAPI()

# カスタム例外ハンドラ (補足されていないエラーが発生した際に、ログを出しつつ安全なレスポンスを返す)
register_exception_handlers(app)

# ミドルウェア: リクエストごとにリクエスト ID を付与し、アクセスログを出力する
app.add_middleware(RequestLoggingMiddleware)

# /api/v1 プレフィックスでルーターを登録
app.include_router(router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Hello World"}

# Kubernetes の probe / ALB ヘルスチェック用。
# liveness は "/"(DB 非依存)、readiness はこの "/health"(DB 疎通)で使い分ける。
# include_in_schema=False で OpenAPI には出さない(フロントの型生成に影響させない)。
@app.get("/health", include_in_schema=False)
def health(
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    try:
        # DB に到達できるかを軽量なクエリで確認する
        session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy"}
    return {"status": "ok"}