import fastapi
import loguru
from fastapi.testclient import TestClient

from app.api.app import API_ROOT_PATH, create_app
from app.core.middleware import RequestLoggingMiddleware


def test_liveness_endpoint_returns_request_id() -> None:
    app = create_app()
    request_logs: list[str] = []
    sink_id = loguru.logger.add(
        lambda message: request_logs.append(str(message)),
        filter=lambda record: record["message"] == "HTTP request completed",
    )
    try:
        with TestClient(app) as client:
            response = client.get(
                f"{API_ROOT_PATH}/v1/healthz/live",
                headers={"X-Request-ID": "test-request-1"},
            )
    finally:
        loguru.logger.remove(sink_id)

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}
    assert response.headers["X-Request-ID"] == "test-request-1"
    assert request_logs == []


def test_regular_request_logs_observability_context() -> None:
    app = fastapi.FastAPI()

    @app.get("/items/{item_id}")
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    app.add_middleware(RequestLoggingMiddleware)

    request_records: list[loguru.Record] = []
    sink_id = loguru.logger.add(
        lambda message: request_records.append(message.record),
        filter=lambda record: record["message"] == "HTTP request completed",
    )
    try:
        with TestClient(app) as client:
            response = client.get(
                "/items/42",
                headers={"X-Request-ID": "test-request-2"},
            )
    finally:
        loguru.logger.remove(sink_id)

    assert response.status_code == 200
    assert len(request_records) == 1
    context = request_records[0]["extra"]
    assert context["request_id"] == "test-request-2"
    assert context["method"] == "GET"
    assert context["path"] == "/items/42"
    assert context["route"] == "/items/{item_id}"
    assert context["status_code"] == 200
    assert isinstance(context["duration_ms"], float)


def test_nested_router_logs_full_route_template() -> None:
    app = fastapi.FastAPI()
    parent_router = fastapi.APIRouter(prefix="/v1")
    child_router = fastapi.APIRouter(prefix="/items")

    @child_router.get("/{item_id}")
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    parent_router.include_router(child_router)
    app.include_router(parent_router)
    app.add_middleware(RequestLoggingMiddleware)

    request_records: list[loguru.Record] = []
    sink_id = loguru.logger.add(
        lambda message: request_records.append(message.record),
        filter=lambda record: record["message"] == "HTTP request completed",
    )
    try:
        with TestClient(app) as client:
            response = client.get("/v1/items/42")
    finally:
        loguru.logger.remove(sink_id)

    assert response.status_code == 200
    assert len(request_records) == 1
    assert request_records[0]["extra"]["route"] == "/v1/items/{item_id}"
