import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import app  # noqa: E402


client = TestClient(app)


def test_health_endpoint_is_available():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "database" in body
    assert "detection" in body


def test_animals_endpoint_returns_collection():
    response = client.get("/api/animals/")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["items"], list)


def test_auth_me_requires_bearer_token():
    response = client.get("/api/auth/me/")
    assert response.status_code == 401


def test_missing_animal_returns_not_found():
    response = client.get("/api/animals/C99999/")
    assert response.status_code == 404
