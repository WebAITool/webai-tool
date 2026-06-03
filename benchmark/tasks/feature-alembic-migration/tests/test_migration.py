"""Tests for feature-alembic-migration task."""
import os
import pytest
from pathlib import Path


@pytest.fixture
def project_dir():
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_alembic_ini_exists(project_dir):
    assert (project_dir / "alembic.ini").exists(), "alembic.ini not found"


def test_alembic_env_exists(project_dir):
    assert (project_dir / "alembic" / "env.py").exists(), "alembic/env.py not found"


def test_initial_migration_exists(project_dir):
    versions = list((project_dir / "alembic" / "versions").glob("*.py"))
    assert len(versions) >= 1, "No migration files found in versions/"


def test_new_migration_exists(project_dir):
    """There should be a second migration for projects and tasks tables."""
    versions = list((project_dir / "alembic" / "versions").glob("*.py"))
    # Exclude __pycache__ and initial
    migration_files = [v for v in versions if "001_initial" not in v.name and "__pycache__" not in str(v)]
    assert len(migration_files) >= 1, "No new migration found (only initial exists)"


def test_migration_has_upgrade_and_downgrade(project_dir):
    """New migration must have both upgrade() and downgrade()."""
    versions = list((project_dir / "alembic" / "versions").glob("*.py"))
    migration_files = [v for v in versions if "001_initial" not in v.name and "__pycache__" not in str(v)]
    assert len(migration_files) >= 1

    content = migration_files[0].read_text(encoding="utf-8")
    assert "def upgrade()" in content, "Missing upgrade() in migration"
    assert "def downgrade()" in content, "Missing downgrade() in migration"


def test_migration_creates_projects_table(project_dir):
    """Migration should create projects table."""
    versions = list((project_dir / "alembic" / "versions").glob("*.py"))
    migration_files = [v for v in versions if "001_initial" not in v.name and "__pycache__" not in str(v)]
    assert len(migration_files) >= 1

    content = migration_files[0].read_text(encoding="utf-8")
    assert "projects" in content, "projects table not mentioned in migration"


def test_migration_creates_tasks_table(project_dir):
    """Migration should create tasks table."""
    versions = list((project_dir / "alembic" / "versions").glob("*.py"))
    migration_files = [v for v in versions if "001_initial" not in v.name and "__pycache__" not in str(v)]
    assert len(migration_files) >= 1

    content = migration_files[0].read_text(encoding="utf-8")
    assert "tasks" in content, "tasks table not mentioned in migration"


def test_migration_has_down_revision(project_dir):
    """New migration should reference the initial migration as down_revision."""
    versions = list((project_dir / "alembic" / "versions").glob("*.py"))
    migration_files = [v for v in versions if "001_initial" not in v.name and "__pycache__" not in str(v)]
    assert len(migration_files) >= 1

    content = migration_files[0].read_text(encoding="utf-8")
    assert "down_revision" in content, "Missing down_revision in migration"
    assert "001_initial" in content, "down_revision should reference 001_initial"


def test_alembic_upgrade_runs(project_dir):
    """alembic upgrade head should succeed."""
    import subprocess
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(project_dir),
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"alembic upgrade head failed: {result.stderr}"


def test_alembic_downgrade_runs(project_dir):
    """alembic downgrade -1 should succeed after upgrade."""
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"], cwd=str(project_dir), capture_output=True, text=True, timeout=60)
    result = subprocess.run(
        ["alembic", "downgrade", "-1"],
        cwd=str(project_dir),
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"alembic downgrade failed: {result.stderr}"
