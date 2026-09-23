import collections.abc
import typing

import fastapi
import fastapi.encoders
import fastapi.exceptions
import fastapi.responses
import starlette.exceptions

from app.api.responses import Error, ErrorResponse


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: collections.abc.Sequence[collections.abc.Mapping[str, typing.Any]] | None = None,
    headers: collections.abc.Mapping[str, str] | None = None,
) -> fastapi.responses.JSONResponse:
    normalized_details = [dict(detail) for detail in details] if details else []
    payload = ErrorResponse(error=Error(code=code, message=message, details=normalized_details))
    return fastapi.responses.JSONResponse(
        status_code=status_code,
        content=fastapi.encoders.jsonable_encoder(payload),
        headers=headers,
    )


def install_error_handlers(app: fastapi.FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(
        _request: fastapi.Request,
        exc: ApiError,
    ) -> fastapi.responses.JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(fastapi.exceptions.RequestValidationError)
    async def validation_error_handler(
        _request: fastapi.Request,
        exc: fastapi.exceptions.RequestValidationError,
    ) -> fastapi.responses.JSONResponse:
        return _error_response(422, "validation_error", "Request validation failed", exc.errors())

    @app.exception_handler(starlette.exceptions.HTTPException)
    async def http_error_handler(
        _request: fastapi.Request,
        exc: starlette.exceptions.HTTPException,
    ) -> fastapi.responses.JSONResponse:
        return _error_response(
            exc.status_code,
            "http_error",
            str(exc.detail),
            headers=exc.headers,
        )
