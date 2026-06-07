import pytest
from fastapi.testclient import TestClient
from pathlib import Path


@pytest.fixture(autouse=True)
def client():
    import sys, importlib
    sys.path.insert(0, "backend")
    import main
    importlib.reload(main)
    return TestClient(main.app)


def test_register_creates_user(client):
    response = client.post("/api/auth/register", json={"username": "testuser", "password": "secret"})
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert "token" in data


def test_login_returns_token(client):
    client.post("/api/auth/register", json={"username": "user1", "password": "pass"})
    response = client.post("/api/auth/login", json={"username": "user1", "password": "pass"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data


def test_items_requires_token(client):
    response = client.get("/api/items")
    assert response.status_code == 401


def test_items_with_token_works(client):
    resp = client.post("/api/auth/register", json={"username": "user2", "password": "pass"})
    token = resp.json()["token"]
    response = client.get("/api/items", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 10


def test_me_endpoint(client):
    resp = client.post("/api/auth/register", json={"username": "meuser", "password": "pass"})
    token = resp.json()["token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "meuser"


def test_frontend_app_has_login_form():
    app_code = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "login" in app_code.lower() or "auth" in app_code.lower()


def test_frontend_stores_token_in_localstorage():
    app_code = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "localStorage" in app_code or "local_storage" in app_code


def test_frontend_attaches_auth_header():
    app_code = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "Authorization" in app_code


def test_frontend_handles_401():
    app_code = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "401" in app_code or "401" in Path("frontend/src/main.js").read_text(encoding="utf-8")


def test_frontend_shows_logout():
    app_code = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    assert "logout" in app_code.lower()