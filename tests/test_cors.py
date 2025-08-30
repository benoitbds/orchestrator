from fastapi.testclient import TestClient
from api.main import app


def test_cors_headers_for_projects_endpoint():
    client = TestClient(app)
    response = client.get(
        "/projects",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_options_handled():
    client = TestClient(app)
    response = client.options(
        "/projects",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
