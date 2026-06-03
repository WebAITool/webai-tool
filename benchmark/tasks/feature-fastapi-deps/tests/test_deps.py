"""Tests for feature-fastapi-deps task."""
import pytest
import os
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def client():
    import importlib, main, database, models
    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(main)
    c = TestClient(main.app)
    yield c
    # Cleanup test db
    if os.path.exists("app.db"):
        os.remove("app.db")


def test_create_item(client):
    resp = client.post("/items", json={"name": "Widget", "price": 9.99, "description": "A widget"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Widget"
    assert data["price"] == 9.99


def test_list_items(client):
    client.post("/items", json={"name": "A", "price": 1.0})
    resp = client.get("/items")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_item(client):
    created = client.post("/items", json={"name": "B", "price": 2.0}).json()
    resp = client.get(f"/items/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "B"


def test_get_item_404(client):
    resp = client.get("/items/9999")
    assert resp.status_code == 404


def test_delete_item(client):
    created = client.post("/items", json={"name": "C", "price": 3.0}).json()
    resp = client.delete(f"/items/{created['id']}")
    assert resp.status_code == 204


def test_delete_item_404(client):
    resp = client.delete("/items/9999")
    assert resp.status_code == 404


def test_uses_dependency_injection():
    """main.py should use Depends(get_db) instead of global list."""
    import inspect, main
    source = inspect.getsource(main)
    assert "Depends(get_db)" in source or "Depends(database.get_db)" in source, \
        "Routes don't use Depends(get_db) — still using global list"


def test_no_global_list():
    """main.py should NOT have _items global list."""
    import inspect, main
    source = inspect.getsource(main)
    assert "_items" not in source or "_items" not in dir(main), \
        "Still using global _items list instead of database"


def test_database_get_db_works():
    """database.get_db() should yield a usable session."""
    from database import get_db, SessionLocal
    assert SessionLocal is not None, "SessionLocal not configured"
    gen = get_db()
    db = next(gen)
    assert db is not None, "get_db() returned None"
    try:
        next(gen)
    except StopIteration:
        pass
