import typing

import fastapi
import pydantic
import sqlalchemy.exc

from app.api.dependencies import OptionalDatabaseDep
from app.api.errors import ApiError
from app.api.responses import ErrorResponse, Response


router = fastapi.APIRouter(prefix="/healthz", tags=["health"])


class Health(pydantic.BaseModel):
    status: typing.Annotated[
        typing.Literal["ok"],
        pydantic.WithJsonSchema(
            {
                "type": "string",
                "enum": ["ok"],
            }
        ),
    ] = "ok"


class HealthResponse(Response[Health]):
    pass


@router.get(
    "/live",
    response_model=HealthResponse,
    operation_id="getLiveness",
)
async def liveness() -> HealthResponse:
    return HealthResponse(data=Health())


@router.get(
    "/ready",
    response_model=HealthResponse,
    operation_id="getReadiness",
    responses={
        503: {
            "model": ErrorResponse,
            "description": "Service unavailable",
        }
    },
)
async def readiness(
    database: OptionalDatabaseDep,
) -> HealthResponse:
    try:
        if database is not None:
            await database.ping()
    except (
        sqlalchemy.exc.SQLAlchemyError,
        OSError,
    ) as exc:
        raise ApiError(503, "not_ready", "A required backing service is unavailable") from exc
    return HealthResponse(data=Health())
