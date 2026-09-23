import uvicorn

from app.core.config import get_settings
from app.core.logging import configure_logging, shutdown_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.logging)
    try:
        uvicorn.run(
            "app.api.app:create_app",
            factory=True,
            host=settings.server.host,
            port=settings.server.port,
            reload=settings.server.reload,
            log_config=None,
            access_log=False,
        )
    finally:
        shutdown_logging()


if __name__ == "__main__":
    main()
