import re
import time
import uuid

import loguru
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


_REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_HEALTHCHECK_ROUTE_PATHS = frozenset({"/v1/healthz/live", "/v1/healthz/ready"})


def _get_request_id(candidate: str | None) -> str:
    if candidate is not None and _VALID_REQUEST_ID.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


def _get_client_ip(scope: Scope) -> str | None:
    client = scope.get("client")
    return client[0] if client else None


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)


def _is_successful_healthcheck(scope: Scope, status_code: int) -> bool:
    return status_code < 400 and _get_route_path(scope) in _HEALTHCHECK_ROUTE_PATHS


def _get_route_path(scope: Scope) -> str | None:
    fastapi_scope = scope.get("fastapi")
    if isinstance(fastapi_scope, dict):
        effective_route = fastapi_scope.get("effective_route_context")
        effective_path = getattr(effective_route, "path_format", None)
        if isinstance(effective_path, str):
            return effective_path

    route = scope.get("route")
    route_path = getattr(route, "path_format", None) or getattr(route, "path", None)
    return route_path if isinstance(route_path, str) else None


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
                    route=_get_route_path(scope),
                ).error("HTTP request raised an exception")
                raise
            else:
                duration_ms = _elapsed_ms(started_at)
                completed_logger = request_logger.bind(
                    status_code=status_code,
                    duration_ms=duration_ms,
                    route=_get_route_path(scope),
                )
                if status_code >= 500:
                    completed_logger.error("HTTP request completed")
                elif status_code >= 400:
                    completed_logger.warning("HTTP request completed")
                elif not _is_successful_healthcheck(scope, status_code):
                    completed_logger.info("HTTP request completed")
