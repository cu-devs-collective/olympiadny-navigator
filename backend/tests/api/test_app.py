from fastapi.testclient import TestClient

from app.api.app import API_ROOT_PATH, create_app


def test_liveness_endpoint_returns_request_id() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            f"{API_ROOT_PATH}/v1/healthz/live",
            headers={"X-Request-ID": "test-request-1"},
        )

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}
    assert response.headers["X-Request-ID"] == "test-request-1"
