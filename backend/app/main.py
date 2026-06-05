from fastapi import FastAPI

from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging
from app.middleware import RequestLoggingMiddleware
from app.routers import router

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