import collections.abc

import sqlalchemy
import sqlalchemy.ext.asyncio

from app.core.config import DatabaseSettings


class Database:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.engine: sqlalchemy.ext.asyncio.AsyncEngine = (
            sqlalchemy.ext.asyncio.create_async_engine(
                settings.url,
                pool_pre_ping=True,
                **(
                    {}
                    if settings.url.startswith("sqlite")
                    else {
                        "pool_size": settings.pool_size,
                        "max_overflow": settings.max_overflow,
                        "pool_timeout": settings.pool_timeout_seconds,
                    }
                ),
            )
        )
        self.session_factory = sqlalchemy.ext.asyncio.async_sessionmaker(
            self.engine,
            class_=sqlalchemy.ext.asyncio.AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def session(self) -> collections.abc.AsyncIterator[sqlalchemy.ext.asyncio.AsyncSession]:
        async with self.session_factory() as session:
            try:
                yield session
            except BaseException:
                await session.rollback()
                raise

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(sqlalchemy.text("SELECT 1"))

    async def close(self) -> None:
        await self.engine.dispose()
