from pydantic_settings import BaseSettings


class Environment(BaseSettings):
    """環境変数から読み込まれる設定オブジェクト"""

    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str

    @property
    def database_url(self) -> str:
        """SQLAlchemy 用の接続 URL を組み立てる"""
        return f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


env = Environment()  # type: ignore[call-arg]
