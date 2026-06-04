import os
import subprocess
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _env_without_api_key() -> dict[str, str]:
    env = os.environ.copy()
    env["API_KEY"] = ""
    env["LLM_API_BASE_URL"] = "https://example.test/v1"
    env["LLM_MODEL"] = "provider/model"
    env["FRONTEND_VISION_MODEL"] = "provider/vision"
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
    assert "API_KEY" in combined_output


def test_ref_project_flow_creates_fresh_output_dir_before_writing_doc(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "provider/vision")

    dev_env_module = types.ModuleType("dev_env")

    class DevEnvConfig:
        def __init__(self, prjdir, commit_branch, enable_commits):
            self.prjdir = prjdir
            self.commit_branch = commit_branch
            self.enable_commits = enable_commits

    dev_env_module.DevEnvConfig = DevEnvConfig
    dev_env_module.prepare_dev_env = lambda config: None
    monkeypatch.setitem(sys.modules, "dev_env", dev_env_module)

    lg_agent_module = types.ModuleType("lg_agent")
    lg_agent_module.get_initial_state = lambda **kwargs: kwargs

    class Agent:
        def invoke(self, state, config):
            return None

    lg_agent_module.create_agent = lambda *args, **kwargs: Agent()
    monkeypatch.setitem(sys.modules, "lg_agent", lg_agent_module)

    logs_module = types.ModuleType("logs")
    logs_module.LOG_FILE = str(tmp_path / "main.log")
    monkeypatch.setitem(sys.modules, "logs", logs_module)

    makesrs_module = types.ModuleType("makesrs_prod")
    makesrs_module.makesrs = lambda ref_path: "# Generated doc\n"
    monkeypatch.setitem(sys.modules, "makesrs_prod", makesrs_module)

    import main

    workspace = tmp_path / "fresh-workspace"
    ref_project = tmp_path / "reference"
    task_path = tmp_path / "task.txt"
    ref_project.mkdir()
    task_path.write_text("Create the project.\n", encoding="utf-8")

    result = main.main(
        [
            "--prjdir",
            str(workspace),
            "--refprjpath",
            str(ref_project),
            str(task_path),
        ]
    )

    assert result == 0
    assert (workspace / "generated_doc.txt").read_text(encoding="utf-8") == (
        "# Generated doc\n"
    )


def test_keyboard_interrupt_reports_short_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "provider/vision")

    dev_env_module = types.ModuleType("dev_env")

    class DevEnvConfig:
        def __init__(self, prjdir, commit_branch, enable_commits):
            self.prjdir = prjdir
            self.commit_branch = commit_branch
            self.enable_commits = enable_commits

    dev_env_module.DevEnvConfig = DevEnvConfig
    dev_env_module.prepare_dev_env = lambda config: None
    monkeypatch.setitem(sys.modules, "dev_env", dev_env_module)

    lg_agent_module = types.ModuleType("lg_agent")
    lg_agent_module.get_initial_state = lambda **kwargs: kwargs

    class Agent:
        def invoke(self, state, config):
            raise KeyboardInterrupt

    lg_agent_module.create_agent = lambda *args, **kwargs: Agent()
    monkeypatch.setitem(sys.modules, "lg_agent", lg_agent_module)

    logs_module = types.ModuleType("logs")
    logs_module.LOG_FILE = str(tmp_path / "main.log")
    monkeypatch.setitem(sys.modules, "logs", logs_module)

    makesrs_module = types.ModuleType("makesrs_prod")
    makesrs_module.makesrs = lambda ref_path: "# Generated doc\n"
    monkeypatch.setitem(sys.modules, "makesrs_prod", makesrs_module)

    import main

    workspace = tmp_path / "workspace"
    doc_path = tmp_path / "project-doc.md"
    task_path = tmp_path / "task.txt"
    doc_path.write_text("# Project\n", encoding="utf-8")
    task_path.write_text("Create the project.\n", encoding="utf-8")

    result = main.main(
        [
            "--prjdir",
            str(workspace),
            "--docpath",
            str(doc_path),
            str(task_path),
        ]
    )

    captured = capsys.readouterr()
    combined_output = captured.out + captured.err
    assert result == 130
    assert "Interrupted by user." in combined_output
    assert "Traceback" not in combined_output
