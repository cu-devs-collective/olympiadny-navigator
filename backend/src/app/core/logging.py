import inspect
import logging
import sys

import loguru

from app.core.config import LoggingSettings


class InterceptHandler(logging.Handler):
    """Forward standard-library records through the Loguru sink."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = loguru.logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        loguru.logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(settings: LoggingSettings) -> None:
    """Configure one output pipeline for application and dependency logs."""

    loguru.logger.remove()
    loguru.logger.add(
        sys.stderr,
        level=settings.level,
        serialize=settings.format == "json",
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )

    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=logging.NOTSET,
        force=True,
    )
    logging.captureWarnings(True)

    _DEPENDENCY_LOGGERS = (
        "fastapi",
        "sqlalchemy.engine",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    )
    for logger_name in _DEPENDENCY_LOGGERS:
        dependency_logger = logging.getLogger(logger_name)
        dependency_logger.handlers.clear()
        dependency_logger.propagate = True

    logging.getLogger("sqlalchemy.engine").setLevel(settings.sql_level)


def shutdown_logging() -> None:
    """Flush queued log records before the process exits."""

    loguru.logger.complete()
