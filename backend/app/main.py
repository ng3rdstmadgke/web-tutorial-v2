from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import setup_logging
from app.exception_handlers import register_exception_handlers
from app.middleware import RequestLoggingMiddleware
from app.routers import router

setup_logging()

app = FastAPI()

# カスタム例外ハンドラ (補足されていないエラーが発生した際に、ログを出しつつ安全なレスポンスを返す)
register_exception_handlers(app)

# ミドルウェア登録（登録順の逆順で実行される）

# ミドルウェア: リクエストごとにリクエスト ID を付与し、アクセスログを出力する
app.add_middleware(RequestLoggingMiddleware)

# ミドルウェア: CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js の開発サーバー
    allow_credentials=True,  # Cookie を送受信するために必要
    allow_methods=["*"],
    allow_headers=["*"],
)

# /api/v1 プレフィックスでルーターを登録
app.include_router(router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Hello World"}