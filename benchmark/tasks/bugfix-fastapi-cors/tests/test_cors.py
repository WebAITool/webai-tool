"""Tests for bugfix-fastapi-cors task."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def client():
    import importlib, main
    importlib.reload(main)
    return TestClient(main.app)


def test_cors_has_specific_origins(client):
    """CORS should allow specific Vue dev origins, not wildcard."""
    response = client.options(
        "/items",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Should not have "Access-Control-Allow-Origin: *" with credentials
    allow_origin = response.headers.get("access-control-allow-origin", "")
    assert allow_origin != "*", "CORS allows wildcard origin with credentials — insecure"


def test_cors_allows_vue_dev_origin(client):
    """Vue dev server origin should be allowed."""
    response = client.options(
        "/items",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin", "")
    assert "5173" in allow_origin, f"Vue dev origin not allowed: {allow_origin}"


def test_cors_allows_put_method(client):
    """PUT method should be allowed for CORS preflight."""
    response = client.options(
        "/items/1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PUT",
        },
    )
    assert response.status_code == 200, f"PUT preflight failed: {response.status_code}"


def test_cors_allows_delete_method(client):
    """DELETE method should be allowed for CORS preflight."""
    response = client.options(
        "/items/1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    assert response.status_code == 200, f"DELETE preflight failed: {response.status_code}"


def test_cors_allows_authorization_header(client):
    """Authorization header should be allowed for JWT auth."""
    response = client.options(
        "/items",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    allow_headers = response.headers.get("access-control-allow-headers", "")
    assert "authorization" in allow_headers.lower(), f"Authorization header not allowed: {allow_headers}"


def test_routes_still_work(client):
    """Existing API routes should still work after CORS fix."""
    resp = client.post("/items", json={"name": "Test", "price": 9.99})
    assert resp.status_code == 201
    resp = client.get("/items")
    assert resp.status_code == 200
