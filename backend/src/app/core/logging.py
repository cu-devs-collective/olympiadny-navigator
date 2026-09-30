import datetime
import inspect
import json
import logging
import sys
import traceback
import typing

import loguru

from app.core.config import LogFormat, LoggingSettings


if typing.TYPE_CHECKING:
    from loguru import Message, Record


_TEXT_LOG_TEMPLATE = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}"
)
_RENDERED_CONTEXT_KEY = "_rendered_context"
_SENSITIVE_HTTP_LOGGER_PREFIXES = (
    "aiohttp.client",
    "h2",
    "hpack",
    "httpcore",
    "httpcore2",
    "httpx",
    "httpx2",
    "hyperframe",
    "urllib3",
)


def _is_verbose_http_record(record: logging.LogRecord) -> bool:
    return record.levelno < logging.WARNING and any(
        record.name == prefix or record.name.startswith(f"{prefix}.")
        for prefix in _SENSITIVE_HTTP_LOGGER_PREFIXES
    )


def _text_log_format(record: "Record") -> str:

    context = " ".join(
        f"{key}={json.dumps(value, default=str, ensure_ascii=False, separators=(',', ':'))}"
        for key, value in sorted(record["extra"].items())
        if not key.startswith("_")
    )
    record["extra"][_RENDERED_CONTEXT_KEY] = context
    context_template = f" | {{extra[{_RENDERED_CONTEXT_KEY}]}}" if context else ""
    return f"{_TEXT_LOG_TEMPLATE}{context_template}\n{{exception}}"


def _json_log_record(record: "Record") -> str:

    timestamp = record["time"].astimezone(datetime.UTC).isoformat(timespec="milliseconds")
    payload: dict[str, typing.Any] = {
        "timestamp": timestamp.replace("+00:00", "Z"),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
    }

    for key, value in record["extra"].items():
        if key.startswith("_"):
            continue
        payload[key if key not in payload else f"context_{key}"] = value

    if exception := record["exception"]:
        payload["exception_type"] = exception.type.__name__ if exception.type is not None else None
        payload["exception_message"] = str(exception.value)
        if exception.type is not None and exception.value is not None:
            payload["exception_traceback"] = "".join(
                traceback.format_exception(
                    exception.type,
                    exception.value,
                    exception.traceback,
                )
            )

    return json.dumps(payload, default=str, ensure_ascii=False, separators=(",", ":"))


def _json_log_sink(message: "Message") -> None:
    sys.stderr.write(f"{_json_log_record(message.record)}\n")
    sys.stderr.flush()


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if _is_verbose_http_record(record):
            return

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

    loguru.logger.remove()
    if settings.format is LogFormat.JSON:
        loguru.logger.add(
            _json_log_sink,
            level=settings.level,
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )
    else:
        loguru.logger.add(
            sys.stderr,
            level=settings.level,
            format=_text_log_format,
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
        "uvicorn.error",
    )
    for logger_name in _DEPENDENCY_LOGGERS:
        dependency_logger = logging.getLogger(logger_name)
        dependency_logger.handlers.clear()
        dependency_logger.propagate = True

    for logger_name in _SENSITIVE_HTTP_LOGGER_PREFIXES:
        http_logger = logging.getLogger(logger_name)
        http_logger.setLevel(logging.WARNING)
        http_logger.handlers.clear()
        http_logger.propagate = True

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.propagate = False
    uvicorn_access_logger.disabled = True

    logging.getLogger("sqlalchemy.engine").setLevel(settings.sql_level)


def shutdown_logging() -> None:

    loguru.logger.complete()
