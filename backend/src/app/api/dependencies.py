import collections.abc
import typing

import fastapi
import httpx2
import sqlalchemy.ext.asyncio

from app.api.errors import ApiError
from app.db.connector import Database


def get_optional_database(request: fastapi.Request) -> Database | None:
    database: Database | None = request.app.state.database
    return database


def get_database(request: fastapi.Request) -> Database:
    database = get_optional_database(request)
    if database is None:
        raise ApiError(503, "database_disabled", "Database connector is not configured")
    return database


async def get_db_session(
    database: typing.Annotated[Database, fastapi.Depends(get_database)],
) -> collections.abc.AsyncIterator[sqlalchemy.ext.asyncio.AsyncSession]:
    async for session in database.session():
        yield session


def get_http_client(request: fastapi.Request) -> httpx2.AsyncClient:
    http_client: httpx2.AsyncClient = request.app.state.http_client
    return http_client


DatabaseDep = typing.Annotated[Database, fastapi.Depends(get_database)]
OptionalDatabaseDep = typing.Annotated[Database | None, fastapi.Depends(get_optional_database)]
DbSessionDep = typing.Annotated[
    sqlalchemy.ext.asyncio.AsyncSession,
    fastapi.Depends(get_db_session),
]
HttpClientDep = typing.Annotated[httpx2.AsyncClient, fastapi.Depends(get_http_client)]
