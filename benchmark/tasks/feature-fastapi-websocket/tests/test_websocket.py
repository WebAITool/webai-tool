import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def client():
    import importlib, main
    importlib.reload(main)
    return TestClient(main.app)


def test_websocket_endpoint_exists():
    import main
    routes = [r.path for r in main.app.routes]
    assert any("/ws" in r for r in routes), "No WebSocket route found"


def test_websocket_connect_and_welcome():
    import main
    from fastapi.testclient import TestClient
    client = TestClient(main.app)
    with client.websocket_connect("/ws/notifications") as ws:
        data = ws.receive_json()
        assert "type" in data, "Welcome message should have a type field"


def test_websocket_receives_item_created_notification():
    import main
    from fastapi.testclient import TestClient
    client = TestClient(main.app)
    with client.websocket_connect("/ws/notifications") as ws:
        ws.receive_json()  # welcome message
        client.post("/items", json={"name": "Keyboard", "price": 79.99})
        data = ws.receive_json()
        assert data["type"] == "item_created", f"Expected item_created, got {data.get('type')}"
        assert "item" in data, "Notification should contain item data"


def test_websocket_receives_item_updated_notification():
    import main
    from fastapi.testclient import TestClient
    client = TestClient(main.app)
    with client.websocket_connect("/ws/notifications") as ws:
        ws.receive_json()  # welcome message
        client.put("/items/1", json={"price": 899.99})
        data = ws.receive_json()
        assert data["type"] == "item_updated", f"Expected item_updated, got {data.get('type')}"
        assert "item" in data, "Notification should contain item data"