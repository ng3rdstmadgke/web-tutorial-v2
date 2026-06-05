from pydantic_settings import BaseSettings


class Environment(BaseSettings):
    """環境変数から読み込まれる設定オブジェクト"""

    # DB 接続情報
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str

    # JWT 設定
    token_secret_key: str = "change-me-in-production"    # noqa: S105  開発用デフォルト。本番は環境変数で必ず上書きする
    token_algorithm: str = "HS256"  # noqa: S105  アルゴリズム名であり秘密情報ではない（誤検知の抑制）:w
    token_expire_minutes: int = 480  # 8 時間

    # Cookie 設定
    cookie_secure: bool = False  # 本番は True (HTTPS 必須)

    # ログフォーマット
    log_format: str = "json"  # "json" or "console"

    @property
    def database_url(self) -> str:
        """SQLAlchemy 用の接続 URL を組み立てる"""
        return f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


env = Environment()  # type: ignore[call-arg]