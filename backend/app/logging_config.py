import logging

import structlog

from app.config import env


def setup_logging() -> None:
    """structlog を設定する。"""
    # 共通のプロセッサ
    shared_processors: list = [
        # コンテキスト変数をイベントに追加
        structlog.contextvars.merge_contextvars,
        # ログレベルを付与
        structlog.stdlib.add_log_level,
        # タイムスタンプを付与 (ISO 8601, UTC)
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # スタックトレースがあればフォーマット
        structlog.processors.StackInfoRenderer(),
        # 例外情報をフォーマット
        structlog.processors.format_exc_info,
    ]

    # レンダラを環境変数で切り替え
    if env.log_format == "console":
        # 開発環境: カラー付きの読みやすいフォーマット
        shared_processors.append(structlog.dev.ConsoleRenderer())
    else:
        # 本番環境: JSON
        shared_processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        # プロセッサチェーン（ログイベントが通るパイプライン）
        processors=shared_processors,
        # structlog のロガーを標準 logging と統合
        wrapper_class=structlog.stdlib.BoundLogger,
        # キャッシュ有効化（パフォーマンス）
        cache_logger_on_first_use=True,
    )

    # 標準 logging のレベル設定（uvicorn のログなど）
    logging.basicConfig(level=logging.INFO, format="%(message)s")