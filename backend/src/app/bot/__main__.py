import asyncio

from app.bot.runner import run_bot
from app.core.config import get_settings
from app.core.logging import configure_logging, shutdown_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.logging)

    try:
        asyncio.run(run_bot(settings))
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_logging()


if __name__ == "__main__":
    main()
