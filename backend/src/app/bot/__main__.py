import asyncio

import loguru

from app.bot.runner import run_bot
from app.core.config import get_settings
from app.core.logging import configure_logging, shutdown_logging


def main() -> int:
    settings = get_settings()
    configure_logging(settings.logging)

    try:
        asyncio.run(run_bot(settings))
    except KeyboardInterrupt:
        return 0
    except Exception:
        loguru.logger.exception("MAX bot terminated unexpectedly")
        return 1
    finally:
        shutdown_logging()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
