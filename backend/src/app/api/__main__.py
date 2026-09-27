import loguru
import uvicorn

from app.core.config import get_settings
from app.core.logging import configure_logging, shutdown_logging


def main() -> int:
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
    except KeyboardInterrupt:
        return 0
    except Exception:
        loguru.logger.exception("API terminated unexpectedly")
        return 1
    finally:
        shutdown_logging()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
