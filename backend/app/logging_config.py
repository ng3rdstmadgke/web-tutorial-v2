import logging.config

import structlog

from app.config import env


class _DropASGIErrorFilter(logging.Filter):
    """uvicorn が出す "Exception in ASGI application" ログを落とすフィルタ。

    未処理例外は exception handler が request_id 付きで JSON 出力する。
    uvicorn の同じ例外ログは重複になるため、ここで取り除く。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn のメッセージは末尾に改行を含む ("Exception in ASGI application\n") ため
        # 完全一致ではなく前方一致で判定する
        return not record.getMessage().startswith("Exception in ASGI application")


# structlog 由来のログと、標準 logging (uvicorn など) 由来のログの両方に通す共通プロセッサ
shared_processors: list = [
    # contextvars の値 (リクエスト ID など) を自動でイベントにマージ
    structlog.contextvars.merge_contextvars,
    # ログレベルを付与
    structlog.stdlib.add_log_level,
    # タイムスタンプを ISO 8601 形式 + UTC で付与 (タイムゾーン非依存で時系列が揃う)
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    # スタック情報があれば付与 (例外の整形は最終のレンダラ側に任せる)
    structlog.processors.StackInfoRenderer(),
]


def setup_logging() -> None:
    """structlog を設定し、uvicorn のログも JSON に統合する。"""
    # --- アプリのログ(structlog) の設定 ---
    structlog.configure(
        # 末尾の wrap_for_formatter で structlog から logging に橋渡し。ログの出力はloggingが行う。
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        # structlog のロガーを標準 logging 上に構築する
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        # キャッシュ有効化(パフォーマンス)
        cache_logger_on_first_use=True,
    )

    # 出力レンダラを環境変数で切り替え (開発: console / 本番: json)
    if env.log_format == "console":
        # 開発環境: カラー付きで読みやすい (ConsoleRenderer が例外も整形する)
        renderer_chain: list = [structlog.dev.ConsoleRenderer()]
    else:
        # 本番環境: JSON (format_exc_info で例外を文字列化してから JSON 化)
        renderer_chain = [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]


    # --- loggingの設定: アプリのログ(structlog)と uvicorn のログの出力先を設定 ---
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "drop_asgi_error": {   # 未処理例外の再ログを落とすフィルタ
                    "()": _DropASGIErrorFilter
                },
            },
            "formatters": {  # ログの整形設定
                # structlog 由来も uvicorn 由来も、この formatter で同じ形に整形する
                "structured": {

                    "()": structlog.stdlib.ProcessorFormatter,  # この Factory を呼び出す
                    "foreign_pre_chain": shared_processors,     # Factory の引数に渡る
                    "processors": [                             # Factory の引数に渡る
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        *renderer_chain,
                    ],
                },
            },
            "handlers": {  # 出力先の設定
                "default": {
                    "class": "logging.StreamHandler",  # 標準ストリームへ出力
                    "formatter": "structured",         # formatter は structured を利用
                },
            },
            # 出力は root に集約する。各 logger は自前ハンドラを持たず root に伝播させる。
            # 例外的に「無効化したいもの」「フィルタを足したいもの」だけここで上書きする
            "loggers": {
                "uvicorn": { # root へ伝播
                    "handlers": [],
                    "level": "INFO",
                    "propagate": True,
                },
                "uvicorn.error": { # 例外ログ ("Exception in ASGI application") だけフィルタ。それ以外は root へ伝播
                    "handlers": [],
                    "level": "INFO",
                    "propagate": True,
                    "filters": ["drop_asgi_error"],
                },
                "uvicorn.access": { # アクセスログは RequestLoggingMiddleware が出すので無効化
                    "handlers": [],
                    "propagate": False,
                },
            },
            "root": {  # アプリ (structlog)、uvicorn、全てのログがここに集約される
                "handlers": ["default"],
                "level": "INFO",
            },
        }
    )