import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI アプリにカスタム例外ハンドラを登録する。"""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """未処理の例外をキャッチし、500 を返す。

        - ユーザーには汎用メッセージだけ返す（スタックトレースを漏らさない）
        - ログにはスタックトレース含む詳細を残す
        """
        logger.error(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            exc_info=exc,  # structlog がスタックトレースをフォーマットしてくれる
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )