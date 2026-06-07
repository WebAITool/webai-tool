import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def client():
    import sys, importlib
    sys.path.insert(0, "backend")
    import main
    importlib.reload(main)
    return TestClient(main.app)


def test_items_returns_paginated_response(client):
    response = client.get("/api/items?page=1&per_page=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data


def test_pagination_defaults(client):
    response = client.get("/api/items")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 10


def test_pagination_second_page(client):
    response = client.get("/api/items?page=2&per_page=10")
    data = response.json()
    assert data["page"] == 2
    assert len(data["items"]) == 10


def test_pagination_last_page(client):
    response = client.get("/api/items?page=10&per_page=10")
    data = response.json()
    assert data["page"] == 10
    assert len(data["items"]) == 10


def test_pagination_total_count(client):
    response = client.get("/api/items?page=1&per_page=10")
    data = response.json()
    assert data["total"] == 100
    assert data["total_pages"] == 10