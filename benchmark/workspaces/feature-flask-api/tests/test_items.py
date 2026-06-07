"""Tests for feature-flask-api task.

These tests FAIL before the feature is implemented and PASS after.
Run: pytest tests/ -v
"""
import pytest
import math
from app.models import Item, _items, _next_id
from app import app


@pytest.fixture(autouse=True)
def clean_items():
    """Reset items store before each test."""
    import app.models as models
    models._items.clear()
    models._next_id = 1
    yield


client = app.test_client()


def _create_items(n, prefix="item"):
    """Helper: create n items via API."""
    for i in range(n):
        client.post("/items", json={"name": f"{prefix}-{i}", "price": i * 10})


def test_basic_list_still_works():
    """Existing GET /items should still return all items."""
    _create_items(3)
    resp = client.get("/items")
    assert resp.status_code == 200
    assert len(resp.json) == 3


def test_search_filters_by_name():
    """GET /items?q=apple should return only matching items."""
    client.post("/items", json={"name": "Apple Pie", "price": 5})
    client.post("/items", json={"name": "Banana Split", "price": 4})
    client.post("/items", json={"name": "Green Apple", "price": 3})

    resp = client.get("/items?q=apple")
    assert resp.status_code == 200
    names = [i["name"] for i in resp.json["items"] if isinstance(resp.json, dict)]
    if not names:
        # Maybe response is still a flat list (not paginated) — check that too
        items = resp.json if isinstance(resp.json, list) else resp.json["items"]
        names = [i["name"] for i in items]
    assert len(names) == 2
    assert "Apple Pie" in names
    assert "Green Apple" in names


def test_search_case_insensitive():
    """Search should be case-insensitive."""
    client.post("/items", json={"name": "Hello World", "price": 1})
    resp = client.get("/items?q=HELLO")
    items = resp.json if isinstance(resp.json, list) else resp.json["items"]
    assert len(items) == 1


def test_pagination_default():
    """GET /items with pagination should return paginated response."""
    _create_items(15)
    resp = client.get("/items?page=1&per_page=5")
    data = resp.json
    assert "items" in data
    assert "page" in data
    assert "total" in data
    assert "pages" in data
    assert data["page"] == 1
    assert data["per_page"] == 5
    assert data["total"] == 15
    assert data["pages"] == 3
    assert len(data["items"]) == 5


def test_pagination_page_2():
    """Second page should have the right items."""
    _create_items(12)
    resp = client.get("/items?page=2&per_page=5")
    data = resp.json
    assert data["page"] == 2
    assert len(data["items"]) == 5


def test_search_with_pagination():
    """Search + pagination should work together."""
    for i in range(10):
        client.post("/items", json={"name": f"Apple {i}", "price": i})
        client.post("/items", json={"name": f"Banana {i}", "price": i})

    resp = client.get("/items?q=apple&page=1&per_page=3")
    data = resp.json
    assert "items" in data
    assert len(data["items"]) == 3
    assert data["total"] == 10
