import asyncio

import alembic.context
import sqlalchemy.engine
import sqlalchemy.ext.asyncio
import sqlalchemy.pool

import app.db.models  # noqa: F401
from app.core.config import get_settings
from app.core.logging import configure_logging, shutdown_logging
from app.db.base import Base


config = alembic.context.config
target_metadata = Base.metadata

configure_logging(get_settings().logging)


def get_database_url() -> str:
    database = get_settings().database
    if database is None:
        raise RuntimeError("APP_DATABASE_URL is required to run migrations")
    return database.url


def run_migrations_offline() -> None:
    alembic.context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with alembic.context.begin_transaction():
        alembic.context.run_migrations()


def run_migrations(connection: sqlalchemy.engine.Connection) -> None:
    alembic.context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with alembic.context.begin_transaction():
        alembic.context.run_migrations()


async def run_migrations_online() -> None:
    engine = sqlalchemy.ext.asyncio.create_async_engine(
        get_database_url(),
        poolclass=sqlalchemy.pool.NullPool,
    )

    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


try:
    if alembic.context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())
finally:
    shutdown_logging()
