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


type LogLevel = typing.Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
type LogFormat = typing.Literal["text", "json"]


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
    level: LogLevel = "INFO"
    sql_level: LogLevel = "WARNING"
    format: LogFormat = "text"


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


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="_",
        env_nested_max_split=1,
        env_prefix="APP_",
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
