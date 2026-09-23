# TODO: remove this example http route file.

import fastapi
import httpx2

from app.api.dependencies import HttpClientDep
from app.api.errors import ApiError
from app.api.responses import ErrorResponse
from app.api.schemas.examples import ExternalTodo, HttpExample, HttpExampleResponse


router = fastapi.APIRouter(prefix="/examples/http", tags=["examples"])

EXAMPLE_API_URL = "https://jsonplaceholder.typicode.com/todos/1"


@router.get(
    "",
    response_model=HttpExampleResponse,
    operation_id="callExampleHttpApi",
    responses={
        502: {
            "model": ErrorResponse,
            "description": "Upstream error",
        }
    },
)
async def call_external_api(http_client: HttpClientDep) -> HttpExampleResponse:
    try:
        response = await http_client.get(EXAMPLE_API_URL)
        response.raise_for_status()
        todo = ExternalTodo.model_validate(response.json())
    except (httpx2.HTTPError, ValueError) as error:
        raise ApiError(502, "upstream_error", "The example upstream API request failed") from error

    return HttpExampleResponse(
        data=HttpExample(
            upstream_id=todo.id,
            title=todo.title,
            completed=todo.completed,
        )
    )
