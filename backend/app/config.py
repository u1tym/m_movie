from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend ディレクトリで uvicorn を起動する前提で、カレントディレクトリの .env を読む
_ENV_FILE = Path.cwd() / ".env"
_env_file: str | None = str(_ENV_FILE) if _ENV_FILE.is_file() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "tamtdb"
    db_user: str = "tamtuser"
    db_password: str = ""

    debug: bool = False
    debug_aid: int = 1

    secret_key: str = "change-me"
    algorithm: str = "HS256"
    cookie_name: str = "access_token"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

# 起動時ログ用
loaded_env_file: str | None = _env_file
