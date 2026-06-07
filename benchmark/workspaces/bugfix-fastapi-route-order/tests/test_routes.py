import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def client():
    import importlib, main
    importlib.reload(main)
    return TestClient(main.app)


def test_items_stats_returns_count(client):
    response = client.get("/items/stats")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] == 2


def test_items_stats_returns_total_value(client):
    response = client.get("/items/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_value" in data
    assert data["total_value"] == 999.99 + 29.99


def test_get_item_by_id(client):
    response = client.get("/items/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Laptop"


def test_get_item_not_found(client):
    response = client.get("/items/999")
    assert response.status_code == 404


def test_list_items(client):
    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2