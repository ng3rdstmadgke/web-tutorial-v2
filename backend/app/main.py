from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import router

app = FastAPI()

# CORS ミドルウェア
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