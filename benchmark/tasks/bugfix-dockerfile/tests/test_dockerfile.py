import pytest
from pathlib import Path


@pytest.fixture
def project_dir():
    return Path(__file__).parent.parent


def test_dockerfile_exists(project_dir):
    assert (project_dir / "backend" / "Dockerfile").exists()


def test_dockerfile_has_correct_workdir(project_dir):
    content = (project_dir / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "WORKDIR" in content, "Dockerfile should use WORKDIR"
    assert "WORKDIRR" not in content, "WORKDIRR is a typo"


def test_dockerfile_copies_correct_path(project_dir):
    content = (project_dir / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.txt" in content
    assert "WORKDIR" in content
    lines = content.splitlines()
    copy_lines = [l for l in lines if l.strip().startswith("COPY")]
    assert len(copy_lines) > 0, "Dockerfile should have COPY instructions"


def test_dockerfile_has_run_instruction(project_dir):
    content = (project_dir / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "RUN" in content, "Dockerfile should have RUN instruction"


def test_dockerfile_has_correct_cmd(project_dir):
    content = (project_dir / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "0.0.0.0" in content, "CMD should bind to 0.0.0.0"