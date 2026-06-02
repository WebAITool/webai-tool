import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _env_without_api_key() -> dict[str, str]:
    env = os.environ.copy()
    env["API_KEY"] = ""
    env.pop("OPENAI_API_KEY", None)
    return env


def test_help_does_not_require_api_key():
    result = subprocess.run(
        [sys.executable, "src/main.py", "--help"],
        cwd=ROOT,
        env=_env_without_api_key(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "usage:" in result.stdout
    assert "--prjdir" in result.stdout


def test_run_without_api_key_reports_clear_configuration_error(tmp_path):
    doc_path = tmp_path / "project-doc.md"
    task_path = tmp_path / "task.txt"
    workspace = tmp_path / "workspace"
    doc_path.write_text("# Project\nCreate a marker file.\n", encoding="utf-8")
    task_path.write_text("Create RESULT.txt with OK.\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "src/main.py",
            "--prjdir",
            str(workspace),
            "--docpath",
            str(doc_path),
            str(task_path),
        ],
        cwd=ROOT,
        env=_env_without_api_key(),
        capture_output=True,
        text=True,
    )

    combined_output = result.stderr + result.stdout
    assert result.returncode != 0
    assert "API_KEY is required" in combined_output
