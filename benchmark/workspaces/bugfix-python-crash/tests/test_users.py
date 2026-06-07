"""Tests for bugfix-python-crash task.

These tests FAIL before the bug is fixed and PASS after.
Run: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Health endpoint should work even before the fix."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_user_returns_201():
    """POST /users should return 201, not 500."""
    resp = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    assert resp.status_code == 201


def test_create_user_returns_user_object():
    """POST /users should return the created user with correct fields."""
    resp = client.post("/users", json={"name": "Bob", "email": "bob@example.com"})
    data = resp.json()
    assert data["name"] == "Bob"
    assert data["email"] == "bob@example.com"
    assert "id" in data


def test_list_users_after_creation():
    """GET /users should return users that were created."""
    client.post("/users", json={"name": "Carol", "email": "carol@example.com"})
    resp = client.get("/users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    assert any(u["name"] == "Carol" for u in users)
