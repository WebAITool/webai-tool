import pytest
from fastapi.testclient import TestClient
import time


@pytest.fixture(autouse=True)
def client():
    import importlib, main
    importlib.reload(main)
    return TestClient(main.app)


def test_response_has_process_time_header(client):
    response = client.get("/items")
    assert "x-process-time" in response.headers or "X-Process-Time" in response.headers


def test_process_time_is_float(client):
    response = client.get("/items")
    header = response.headers.get("x-process-time", response.headers.get("X-Process-Time", ""))
    assert header, "Missing X-Process-Time header"
    try:
        float(header)
    except ValueError:
        assert False, f"X-Process-Time header is not a number: {header}"


def test_logging_is_configured(client):
    import logging
    logger = logging.getLogger()
    assert logger.hasHandlers(), "No logging handlers configured"


def test_all_endpoints_have_process_time(client):
    for path in ["/items", "/items/1"]:
        response = client.get(path)
        header = response.headers.get("x-process-time", response.headers.get("X-Process-Time", ""))
        assert header, f"Missing X-Process-Time for {path}"