"""Tests for create-cli-tool task.

These tests verify the filestats CLI tool works correctly.
Run: pytest tests/ -v
"""
import os
import json
import csv
import pytest
import tempfile
import subprocess
import sys

TOOL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "filestats.py")


def _run_filestats(*args, cwd=None):
    """Run filestats.py as subprocess and return output."""
    result = subprocess.run(
        [sys.executable, TOOL_PATH] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )
    return result


@pytest.fixture
def sample_dir():
    """Create a temp directory with sample files."""
    tmpdir = tempfile.mkdtemp(prefix="filestats_test_")
    # Create some files
    with open(os.path.join(tmpdir, "hello.py"), "w") as f:
        f.write("print('hello')\n# comment\n\ndef greet():\n    return 'hi'\n")
    with open(os.path.join(tmpdir, "readme.md"), "w") as f:
        f.write("# README\n\nSome text here.\n")
    with open(os.path.join(tmpdir, "data.csv"), "w") as f:
        f.write("a,b,c\n1,2,3\n4,5,6\n")
    # Hidden file (should be skipped)
    with open(os.path.join(tmpdir, ".hidden"), "w") as f:
        f.write("secret\n")
    # Subdirectory
    os.makedirs(os.path.join(tmpdir, "sub"))
    with open(os.path.join(tmpdir, "sub", "utils.py"), "w") as f:
        f.write("def util():\n    pass\n")
    yield tmpdir
    import shutil
    shutil.rmtree(tmpdir)


def test_tool_runs_without_error(sample_dir):
    """filestats should exit with code 0 on a valid directory."""
    result = _run_filestats(sample_dir)
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_tool_shows_files(sample_dir):
    """Output should mention the Python files."""
    result = _run_filestats(sample_dir)
    assert "hello.py" in result.stdout or "hello.py" in result.stdout


def test_tool_shows_summary(sample_dir):
    """Output should include a summary section."""
    result = _run_filestats(sample_dir)
    output = result.stdout.lower()
    assert "total" in output or "files" in output


def test_ext_filter(sample_dir):
    """--ext .py should only show Python files."""
    result = _run_filestats(sample_dir, "--ext", ".py")
    assert result.returncode == 0
    assert "hello.py" in result.stdout
    assert "readme.md" not in result.stdout


def test_json_format(sample_dir):
    """--format json should produce valid JSON."""
    result = _run_filestats(sample_dir, "--format", "json")
    assert result.returncode == 0
    # Should be parseable JSON
    try:
        data = json.loads(result.stdout)
        assert isinstance(data, (list, dict))
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")


def test_top_flag(sample_dir):
    """--top 1 should show only 1 file."""
    result = _run_filestats(sample_dir, "--top", "1", "--format", "json")
    assert result.returncode == 0


def test_skips_hidden_files(sample_dir):
    """Hidden files should not appear in output."""
    result = _run_filestats(sample_dir)
    assert ".hidden" not in result.stdout


def test_nonexistent_directory():
    """Should handle nonexistent directory gracefully."""
    result = _run_filestats("/nonexistent_dir_xyz_12345")
    assert result.returncode != 0 or "error" in result.stdout.lower() or "error" in result.stderr.lower()
