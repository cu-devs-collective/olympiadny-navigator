import re
import time
import uuid

import loguru
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


_REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _get_request_id(candidate: str | None) -> str:
    if candidate is not None and _VALID_REQUEST_ID.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


def _get_client_ip(scope: Scope) -> str | None:
    client = scope.get("client")
    return client[0] if client else None


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)


class RequestLoggingMiddleware:
    """Attach a request ID and log the completion or failure of each HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _get_request_id(Headers(scope=scope).get(_REQUEST_ID_HEADER))
        started_at = time.perf_counter()
        status_code = 500
        method = scope["method"]
        path = scope["path"]

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[_REQUEST_ID_HEADER] = request_id
            await send(message)

        with loguru.logger.contextualize(request_id=request_id):
            request_logger = loguru.logger.bind(
                method=method,
                path=path,
                client_ip=_get_client_ip(scope),
            )
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception:
                duration_ms = _elapsed_ms(started_at)
                request_logger.bind(
                    status_code=status_code,
                    duration_ms=duration_ms,
                ).error("Request failed")
                raise
            else:
                duration_ms = _elapsed_ms(started_at)
                completed_logger = request_logger.bind(
                    status_code=status_code, duration_ms=duration_ms
                )
                if status_code >= 500:
                    completed_logger.error("Request failed")
                else:
                    completed_logger.info("Request completed")
