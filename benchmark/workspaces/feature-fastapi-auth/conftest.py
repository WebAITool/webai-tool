import sys
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(autouse=True)
def fresh_app():
    # Ensure fresh imports each test to reset state
    for mod_name in list(sys.modules.keys()):
        if mod_name in ('auth', 'main'):
            del sys.modules[mod_name]
    import main
    return main.app

@pytest.fixture
def client(fresh_app):
    return TestClient(fresh_app)
