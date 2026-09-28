import collections.abc
import contextlib

import fastapi
import fastapi.middleware.cors
import httpx2
import loguru

from app.api.errors import install_error_handlers
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, shutdown_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.connector import Database


OPENAPI_VERSION = "3.1.0"
API_ROOT_PATH = "/api"


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> collections.abc.AsyncGenerator[None]:
    settings: Settings = app.state.settings
    database = Database(settings.database) if settings.database is not None else None
    http_client = httpx2.AsyncClient()
    app.state.database = database
    app.state.http_client = http_client

    loguru.logger.info("API service started")
    try:
        yield
    finally:
        await http_client.aclose()
        if database is not None:
            await database.close()
        loguru.logger.info("API service stopped")
        shutdown_logging()


def create_app(settings: Settings | None = None) -> fastapi.FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.logging)

    app = fastapi.FastAPI(
        title="Олимпиадный маршрут",
        version="0.1.0",
        root_path=API_ROOT_PATH,
        servers=[{"url": API_ROOT_PATH}],
        openapi_tags=[{"name": "health", "description": "Service health checks."}],
        lifespan=lifespan,
        debug=settings.debug,
    )

    app.openapi_version = OPENAPI_VERSION
    app.state.settings = settings

    if settings.cors is not None:
        app.add_middleware(
            fastapi.middleware.cors.CORSMiddleware,
            allow_origins=settings.cors.allow_origins,
            allow_credentials=settings.cors.allow_credentials,
            allow_methods=settings.cors.allow_methods,
            allow_headers=settings.cors.allow_headers,
            expose_headers=settings.cors.expose_headers,
            max_age=settings.cors.max_age,
        )

    app.add_middleware(RequestLoggingMiddleware)
    install_error_handlers(app)
    app.include_router(api_router)

    return app
