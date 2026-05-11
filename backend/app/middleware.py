import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """リクエストごとにリクエスト ID を付与し、アクセスログを出力する。"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # リクエスト ID を生成
        request_id = str(uuid.uuid4())

        # FastAPI(uvicorn)はリクエストを処理するworkerを再利用するため、以前のリクエストのcontextvarsを消去します
        structlog.contextvars.clear_contextvars()

        # リクエスト用の contextvars をバインド（以降このリクエスト内の全ログに自動付与される）
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # 処理時間の計測開始
        start_time = time.perf_counter()

        # リクエスト処理を実行
        response = await call_next(request)

        # 処理時間を計算
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # レスポンスヘッダにリクエスト ID を追加
        response.headers["X-Request-ID"] = request_id

        # アクセスログを出力
        await logger.ainfo(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response