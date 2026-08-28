from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    """Verify the health endpoint returns expected response on GET."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "recoveriq-api"


def test_health_endpoint_rejects_post():
    """Verify the health endpoint rejects POST with 405 Method Not Allowed."""
    response = client.post("/health")
    assert response.status_code == 405
