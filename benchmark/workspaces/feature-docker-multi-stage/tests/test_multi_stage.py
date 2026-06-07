import pytest
from pathlib import Path


@pytest.fixture
def project_dir():
    return Path(__file__).parent.parent


def test_backend_dockerfile_has_multi_stage(project_dir):
    content = (project_dir / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert content.count("FROM") >= 2, "Backend Dockerfile should have at least 2 FROM statements (multi-stage)"


def test_frontend_dockerfile_has_multi_stage(project_dir):
    content = (project_dir / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert content.count("FROM") >= 2, "Frontend Dockerfile should have at least 2 FROM statements (multi-stage)"


def test_backend_dockerfile_uses_slim(project_dir):
    content = (project_dir / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "slim" in content, "Backend runtime stage should use slim image"


def test_frontend_dockerfile_uses_nginx(project_dir):
    content = (project_dir / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert "nginx" in content, "Frontend production stage should use nginx"


def test_docker_compose_prod_exists(project_dir):
    assert (project_dir / "docker-compose.prod.yml").exists()


def test_docker_compose_prod_has_env(project_dir):
    content = (project_dir / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "production" in content.lower(), "Production compose should set production environment"


def test_docker_compose_prod_has_nginx(project_dir):
    content = (project_dir / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "nginx" in content, "Production compose should have nginx service"


def test_dev_docker_compose_exists(project_dir):
    assert (project_dir / "docker-compose.yml").exists(), "Development docker-compose.yml should be kept"