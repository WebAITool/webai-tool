"""Tests for refactor-fastapi-routers task."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def client():
    # Must import from the new app package
    import importlib
    import sys
    from pathlib import Path
    
    # Add project directory to sys.path
    project_dir = Path(__file__).parent.parent / ""
    sys.path.append(str(project_dir))
    
    try:
        import app as app_pkg
        importlib.reload(app_pkg)
        return TestClient(app_pkg.app)
    except ImportError:
        # Fallback: old monolithic main
        import main
        importlib.reload(main)
        return TestClient(main.app)


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_user_crud(client):
    # Create
    resp = client.post("/users", json={"username": "alice", "email": "a@b.com"})
    assert resp.status_code == 201
    uid = resp.json()["id"]
    # List
    resp = client.get("/users")
    assert resp.status_code == 200
    # Get
    resp = client.get(f"/users/{uid}")
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"
    # Delete
    resp = client.delete(f"/users/{uid}")
    assert resp.status_code == 204


def test_item_crud(client):
    resp = client.post("/items", json={"name": "Widget", "price": 9.99})
    assert resp.status_code == 201
    iid = resp.json()["id"]
    resp = client.get("/items")
    assert resp.status_code == 200
    resp = client.get(f"/items/{iid}")
    assert resp.status_code == 200
    resp = client.delete(f"/items/{iid}")
    assert resp.status_code == 204


def test_app_package_exists():
    """app/ package should exist after refactor."""
    from pathlib import Path
    project_dir = Path(__file__).parent.parent / ""
    assert (project_dir / "app" / "__init__.py").exists(), "app/__init__.py not found"


def test_routers_package_exists():
    """app/routers/ package should exist after refactor."""
    from pathlib import Path
    project_dir = Path(__file__).parent.parent / ""
    assert (project_dir / "app" / "routers" / "__init__.py").exists(), "app/routers/__init__.py not found"


def test_health_router_file_exists():
    """app/routers/health.py should exist."""
    from pathlib import Path
    project_dir = Path(__file__).parent.parent / ""
    assert (project_dir / "app" / "routers" / "health.py").exists(), "app/routers/health.py not found"


def test_users_router_file_exists():
    """app/routers/users.py should exist."""
    from pathlib import Path
    project_dir = Path(__file__).parent.parent / ""
    assert (project_dir / "app" / "routers" / "users.py").exists(), "app/routers/users.py not found"


def test_items_router_file_exists():
    """app/routers/items.py should exist."""
    from pathlib import Path
    project_dir = Path(__file__).parent.parent / ""
    assert (project_dir / "app" / "routers" / "items.py").exists(), "app/routers/items.py not found"


def test_routers_use_api_router():
    """Router files should use APIRouter."""
    from pathlib import Path
    project_dir = Path(__file__).parent.parent
    for name in ["health.py", "users.py", "items.py"]:
        path = project_dir / "app" / "routers" / name
        if path.exists():
            content = path.read_text(encoding="utf-8")
            assert "APIRouter" in content, f"{name} doesn't use APIRouter"
