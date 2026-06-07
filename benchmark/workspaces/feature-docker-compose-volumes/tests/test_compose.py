import pytest
from pathlib import Path


@pytest.fixture
def project_dir():
    return Path(__file__).parent.parentdef test_docker_compose_exists(project_dir):
    assert (project_dir / "docker-compose.yml").exists()


def test_docker_compose_has_backend_service(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "backend" in content


def test_docker_compose_has_frontend_service(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "frontend" in content


def test_docker_compose_has_volumes(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "volumes" in content, "docker-compose should have volumes configuration"


def test_docker_compose_ports_backend(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "8000" in content, "Backend should expose port 8000"


def test_docker_compose_ports_frontend(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "5173" in content, "Frontend should expose port 5173"


def test_docker_compose_has_network(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "network" in content.lower() or "networks" in content.lower()


def test_backend_uses_reload(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "--reload" in content, "Backend should use --reload for dev"


def test_frontend_uses_host(project_dir):
    content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "--host" in content, "Frontend should expose host for dev"