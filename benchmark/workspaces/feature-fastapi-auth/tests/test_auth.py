"""Tests for feature-fastapi-auth task."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def fresh_app():
    """Re-import app and auth each test to reset state."""
    import importlib
    import main
    import auth
    importlib.reload(auth)
    importlib.reload(main)
    return main.app
def client(fresh_app):
    return TestClient(fresh_app)


def _register(client, username="alice", password="pass123"):
    return client.post("/auth/register", json={"username": username, "password": password})


def _login(client, username="alice", password="pass123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_register(client):
    resp = _register(client)
    assert resp.status_code == 200 or resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["username"] == "alice"


def test_login(client):
    _register(client)
    resp = _login(client)
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password(client):
    _register(client)
    resp = _login(client, password="wrong")
    assert resp.status_code in (401, 403)


def test_notes_require_auth(client):
    resp = client.get("/notes")
    assert resp.status_code == 401 or resp.status_code == 403


def test_create_note_with_auth(client):
    token = _register(client).json()["token"]
    resp = client.post("/notes", json={"title": "Test", "content": "Hello"}, headers=_auth_header(token))
    assert resp.status_code == 201


def test_list_notes_with_auth(client):
    token = _register(client).json()["token"]
    client.post("/notes", json={"title": "My Note", "content": "x"}, headers=_auth_header(token))
    resp = client.get("/notes", headers=_auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_notes_per_user(client):
    token1 = _register(client, "user1", "pw1").json()["token"]
    token2 = _register(client, "user2", "pw2").json()["token"]
    client.post("/notes", json={"title": "Note1", "content": "a"}, headers=_auth_header(token1))
    client.post("/notes", json={"title": "Note2", "content": "b"}, headers=_auth_header(token2))

    notes1 = client.get("/notes", headers=_auth_header(token1)).json()
    notes2 = client.get("/notes", headers=_auth_header(token2)).json()

    assert len(notes1) == 1
    assert len(notes2) == 1
    assert notes1[0]["title"] == "Note1"
    assert notes2[0]["title"] == "Note2"


def test_invalid_token(client):
    resp = client.get("/notes", headers=_auth_header("invalid.token.here"))
    assert resp.status_code in (401, 403)
