"""Tests for create-docker-setup task."""
import pytest
from pathlib import Path


@pytest.fixture
def project_dir():
    return Path(__file__).parent.parent / "project"


def test_backend_dockerfile_exists(project_dir):
    assert (project_dir / "backend" / "Dockerfile").exists(), "backend/Dockerfile not found"


def test_frontend_dockerfile_exists(project_dir):
    assert (project_dir / "frontend" / "Dockerfile").exists(), "frontend/Dockerfile not found"


def test_docker_compose_exists(project_dir):
    assert (project_dir / "docker-compose.yml").exists(), "docker-compose.yml not found"


def test_nginx_conf_exists(project_dir):
    assert (project_dir / "nginx.conf").exists(), "nginx.conf not found"


def test_backend_dockerfile_content(project_dir):
    content = (project_dir / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "python" in content.lower(), "Backend Dockerfile should use Python base image"
    assert "requirements" in content.lower(), "Should install requirements"
    assert "uvicorn" in content.lower(), "Should run uvicorn"


def test_frontend_dockerfile_content(project_dir):
    content = (project_dir / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert "node" in content.lower(), "Frontend Dockerfile should use Node base image"
    assert "npm" in content.lower(), "Should run npm install"


def test_docker_compose_has_services(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "backend" in content, "Missing backend service"
    assert "frontend" in content, "Missing frontend service"
    assert "nginx" in content, "Missing nginx service"


def test_docker_compose_has_network(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "network" in content.lower(), "Missing network configuration"


def test_docker_compose_depends_on(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "depends_on" in content, "Missing depends_on for service ordering"


def test_nginx_proxies_api(project_dir):
    content = (project_dir / "nginx.conf").read_text(encoding="utf-8")
    assert "/api" in content, "nginx should proxy /api to backend"
    assert "backend" in content, "nginx should reference backend service"


def test_nginx_proxies_frontend(project_dir):
    content = (project_dir / "nginx.conf").read_text(encoding="utf-8")
    assert "frontend" in content, "nginx should proxy to frontend service"


def test_nginx_websocket_support(project_dir):
    content = (project_dir / "nginx.conf").read_text(encoding="utf-8")
    assert "Upgrade" in content, "nginx should support WebSocket upgrade for Vite HMR"


def test_backend_dockerignore(project_dir):
    path = project_dir / "backend" / ".dockerignore"
    assert path.exists(), "backend/.dockerignore not found"


def test_frontend_dockerignore(project_dir):
    path = project_dir / "frontend" / ".dockerignore"
    assert path.exists(), "frontend/.dockerignore not found"
