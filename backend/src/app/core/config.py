import enum
import functools
import typing

import pydantic
import pydantic_settings
import sqlalchemy.engine
import sqlalchemy.exc


class ServerSettings(pydantic.BaseModel):
    host: str = "0.0.0.0"
    port: int = pydantic.Field(default=8000, ge=1, le=65535)
    reload: bool = False


class LogLevel(enum.StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(enum.StrEnum):
    TEXT = "text"
    JSON = "json"


class BotMode(enum.StrEnum):
    LONG_POLLING = "long_polling"
    WEBHOOK = "webhook"


class DatabaseSettings(pydantic.BaseModel):
    url: str
    pool_size: int = pydantic.Field(default=5, ge=1)
    max_overflow: int = pydantic.Field(default=10, ge=0)
    pool_timeout_seconds: float = pydantic.Field(default=30.0, gt=0)

    @pydantic.field_validator("url")
    @classmethod
    def require_async_psycopg_driver(cls, value: str) -> str:
        try:
            url = sqlalchemy.engine.make_url(value)
        except sqlalchemy.exc.ArgumentError as error:
            raise ValueError("Database URL must be a valid SQLAlchemy URL") from error

        if url.drivername != "postgresql+psycopg":
            raise ValueError("Database URL must use the postgresql+psycopg async driver")

        return value


class LoggingSettings(pydantic.BaseModel):
    level: LogLevel = LogLevel.INFO
    sql_level: LogLevel = LogLevel.WARNING
    format: LogFormat = LogFormat.TEXT


class CorsSettings(pydantic.BaseModel):
    allow_origins: list[str] = pydantic.Field(min_length=1)
    allow_credentials: bool = False
    allow_methods: list[str] = pydantic.Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    allow_headers: list[str] = pydantic.Field(
        default_factory=lambda: ["Authorization", "Content-Type", "X-Request-ID"]
    )
    expose_headers: list[str] = pydantic.Field(default_factory=lambda: ["X-Request-ID"])
    max_age: int = pydantic.Field(default=600, ge=0)

    @pydantic.model_validator(mode="after")
    def reject_wildcard_origin_with_credentials(self) -> typing.Self:
        if self.allow_credentials and "*" in self.allow_origins:
            raise ValueError("CORS wildcard origin cannot be used with credentials")
        return self


class BotSettings(pydantic.BaseModel):
    token: pydantic.SecretStr
    mode: BotMode = BotMode.LONG_POLLING
    webhook_url: pydantic.HttpUrl | None = None
    webhook_secret: pydantic.SecretStr | None = None
    webhook_host: str = "0.0.0.0"
    webhook_port: int = pydantic.Field(default=8080, ge=1, le=65535)
    webhook_path: str = "/webhook"

    @pydantic.field_validator("webhook_url")
    @classmethod
    def require_https_webhook(cls, value: pydantic.HttpUrl | None) -> pydantic.HttpUrl | None:
        if value is not None and value.scheme != "https":
            raise ValueError("MAX webhook URL must use HTTPS")
        return value

    @pydantic.field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, value: pydantic.SecretStr | None) -> pydantic.SecretStr | None:
        if value is None:
            return value

        secret = value.get_secret_value()
        allowed = all(
            character.isascii() and (character.isalnum() or character == "-")
            for character in secret
        )
        if not 5 <= len(secret) <= 256 or not allowed:
            raise ValueError(
                "MAX webhook secret must contain 5-256 ASCII letters, digits, or hyphens"
            )
        return value

    @pydantic.field_validator("webhook_path")
    @classmethod
    def require_absolute_webhook_path(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("MAX webhook path must start with exactly one slash")
        return value

    @pydantic.model_validator(mode="after")
    def require_webhook_credentials_in_webhook_mode(self) -> typing.Self:
        if self.mode is BotMode.WEBHOOK and (
            self.webhook_url is None or self.webhook_secret is None
        ):
            raise ValueError("Webhook mode requires APP_BOT_WEBHOOK_URL and APP_BOT_WEBHOOK_SECRET")
        return self


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="_",
        env_nested_max_split=1,
        env_prefix="APP_",
        env_ignore_empty=True,
        extra="ignore",
    )

    debug: bool = False
    server: ServerSettings = pydantic.Field(default_factory=ServerSettings)
    logging: LoggingSettings = pydantic.Field(default_factory=LoggingSettings)
    cors: CorsSettings | None = None
    database: DatabaseSettings | None = None
    bot: BotSettings | None = None


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
