import os
import subprocess
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


PROVIDER_ENV_NAMES = (
    "API_KEY",
    "LLM_API_BASE_URL",
    "LLM_MODEL",
    "FRONTEND_VISION_MODEL",
)

CODE_EXECUTOR_ENV_NAMES = (
    "CODE_EXECUTOR",
    "CODE_EXECUTOR_IMAGE",
    "CODE_EXECUTOR_DOCKER_NETWORK",
    "CODE_EXECUTOR_TIMEOUT_SECONDS",
    "CODE_EXECUTOR_OUTPUT_LIMIT_BYTES",
    "CODE_EXECUTOR_MEMORY",
    "CODE_EXECUTOR_CPUS",
    "CODE_EXECUTOR_PIDS_LIMIT",
)


def _env_without_api_key() -> dict[str, str]:
    env = os.environ.copy()
    env["API_KEY"] = ""
    env["LLM_API_BASE_URL"] = "https://example.test/v1"
    env["LLM_MODEL"] = "provider/model"
    env["FRONTEND_VISION_MODEL"] = "provider/vision"
    env.pop("OPENAI_API_KEY", None)
    return env


def _clear_env(monkeypatch, names):
    for name in names:
        monkeypatch.delenv(name, raising=False)


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


def test_parser_accepts_docker_code_executor(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))

    import main

    args = main.build_parser().parse_args(
        [
            "--prjdir",
            "/tmp/project",
            "--docpath",
            "/tmp/doc.md",
            "--code-executor",
            "docker",
            "--code-executor-image",
            "webai-tool:test",
            "--code-executor-network",
            "none",
            "/tmp/task.txt",
        ]
    )

    assert args.code_executor == "docker"
    assert args.code_executor_image == "webai-tool:test"
    assert args.code_executor_network == "none"


def test_parser_reads_code_executor_defaults_from_env(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    monkeypatch.setenv("CODE_EXECUTOR", "docker")
    monkeypatch.setenv("CODE_EXECUTOR_IMAGE", "webai-tool:env")
    monkeypatch.setenv("CODE_EXECUTOR_DOCKER_NETWORK", "bridge")

    import main

    args = main.build_parser().parse_args(
        [
            "--prjdir",
            "/tmp/project",
            "--docpath",
            "/tmp/doc.md",
            "/tmp/task.txt",
        ]
    )

    assert args.code_executor == "docker"
    assert args.code_executor_image == "webai-tool:env"
    assert args.code_executor_network == "bridge"


def test_parser_reads_code_executor_defaults_from_env_file(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    _clear_env(monkeypatch, CODE_EXECUTOR_ENV_NAMES)
    env_file = tmp_path / "agent.env"
    env_file.write_text(
        "\n".join(
            [
                "CODE_EXECUTOR=docker",
                "CODE_EXECUTOR_IMAGE=webai-tool:file",
                "CODE_EXECUTOR_DOCKER_NETWORK=bridge",
            ]
        ),
        encoding="utf-8",
    )

    import main

    args = main.build_parser().parse_args(
        [
            "--env-file",
            str(env_file),
            "--prjdir",
            "/tmp/project",
            "--docpath",
            "/tmp/doc.md",
            "/tmp/task.txt",
        ]
    )

    assert args.code_executor == "docker"
    assert args.code_executor_image == "webai-tool:file"
    assert args.code_executor_network == "bridge"


def test_parser_cli_flag_overrides_env_file(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    _clear_env(monkeypatch, CODE_EXECUTOR_ENV_NAMES)
    env_file = tmp_path / "agent.env"
    env_file.write_text(
        "\n".join(
            [
                "CODE_EXECUTOR=docker",
                "CODE_EXECUTOR_IMAGE=webai-tool:file",
            ]
        ),
        encoding="utf-8",
    )

    import main

    args = main.build_parser().parse_args(
        [
            "--env-file",
            str(env_file),
            "--prjdir",
            "/tmp/project",
            "--docpath",
            "/tmp/doc.md",
            "--code-executor",
            "host",
            "/tmp/task.txt",
        ]
    )

    assert args.code_executor == "host"
    assert args.code_executor_image == "webai-tool:file"


def test_parser_process_env_overrides_env_file(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    _clear_env(monkeypatch, CODE_EXECUTOR_ENV_NAMES)
    monkeypatch.setenv("CODE_EXECUTOR", "host")
    env_file = tmp_path / "agent.env"
    env_file.write_text(
        "\n".join(
            [
                "CODE_EXECUTOR=docker",
                "CODE_EXECUTOR_IMAGE=webai-tool:file",
            ]
        ),
        encoding="utf-8",
    )

    import main

    args = main.build_parser().parse_args(
        [
            "--env-file",
            str(env_file),
            "--prjdir",
            "/tmp/project",
            "--docpath",
            "/tmp/doc.md",
            "/tmp/task.txt",
        ]
    )

    assert args.code_executor == "host"
    assert args.code_executor_image == "webai-tool:file"


def test_parser_env_file_does_not_fall_back_to_dotenv(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    _clear_env(monkeypatch, CODE_EXECUTOR_ENV_NAMES)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "CODE_EXECUTOR=docker",
                "CODE_EXECUTOR_IMAGE=webai-tool:dotenv",
            ]
        ),
        encoding="utf-8",
    )
    env_file = tmp_path / "agent.env"
    env_file.write_text(
        "\n".join(
            [
                "CODE_EXECUTOR=docker",
                "CODE_EXECUTOR_DOCKER_NETWORK=bridge",
            ]
        ),
        encoding="utf-8",
    )

    import main

    try:
        main.build_parser().parse_args(
            [
                "--env-file",
                str(env_file),
                "--prjdir",
                "/tmp/project",
                "--docpath",
                "/tmp/doc.md",
                "/tmp/task.txt",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("explicit --env-file should not backfill from .env")


def test_parser_rejects_missing_env_file(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))

    import main

    try:
        main.build_parser().parse_args(
            [
                "--env-file",
                str(tmp_path / "missing.env"),
                "--prjdir",
                "/tmp/project",
                "--docpath",
                "/tmp/doc.md",
                "/tmp/task.txt",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("missing --env-file should fail at parse time")


def test_parser_rejects_invalid_code_executor_env(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    monkeypatch.setenv("CODE_EXECUTOR", "bogus")

    import main

    try:
        main.build_parser().parse_args(
            [
                "--prjdir",
                "/tmp/project",
                "--docpath",
                "/tmp/doc.md",
                "/tmp/task.txt",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("invalid CODE_EXECUTOR should fail at parse time")


def test_parser_requires_image_for_docker_executor(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    _clear_env(monkeypatch, CODE_EXECUTOR_ENV_NAMES)
    monkeypatch.chdir(tmp_path)

    import main

    try:
        main.build_parser().parse_args(
            [
                "--prjdir",
                "/tmp/project",
                "--docpath",
                "/tmp/doc.md",
                "--code-executor",
                "docker",
                "/tmp/task.txt",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("docker executor should require an explicit image")


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
    monkeypatch.setenv("CODE_EXECUTOR", "host")

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
    lg_agent_module.CodeExecutionConfig = lambda **kwargs: kwargs

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


def test_main_loads_provider_config_from_env_file(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    _clear_env(monkeypatch, PROVIDER_ENV_NAMES + CODE_EXECUTOR_ENV_NAMES)
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / "agent.env"
    env_file.write_text(
        "\n".join(
            [
                "API_KEY=file-key",
                "LLM_API_BASE_URL=https://example.test/v1",
                "LLM_MODEL=provider/from-file",
                "FRONTEND_VISION_MODEL=provider/vision-from-file",
            ]
        ),
        encoding="utf-8",
    )

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
    lg_agent_module.CodeExecutionConfig = lambda **kwargs: kwargs
    captured = {}

    class Agent:
        def invoke(self, state, config):
            captured["state"] = state

    def create_agent(enable_commits, interactive, llm_config):
        captured["llm_config"] = llm_config
        return Agent()

    lg_agent_module.create_agent = create_agent
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
            "--env-file",
            str(env_file),
            "--prjdir",
            str(workspace),
            "--docpath",
            str(doc_path),
            str(task_path),
        ]
    )

    assert result == 0
    assert captured["llm_config"].api_key == "file-key"
    assert captured["llm_config"].model == "provider/from-file"
    assert captured["state"]["code_execution"]["executor"] == "host"


def test_main_does_not_backfill_missing_provider_values_from_repo_dotenv(
    tmp_path, monkeypatch
):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    _clear_env(monkeypatch, PROVIDER_ENV_NAMES + CODE_EXECUTOR_ENV_NAMES)
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / "agent.env"
    env_file.write_text(
        "\n".join(
            [
                "API_KEY=file-key",
                "LLM_API_BASE_URL=https://example.test/v1",
                "LLM_MODEL=provider/from-file",
            ]
        ),
        encoding="utf-8",
    )

    import main

    workspace = tmp_path / "workspace"
    doc_path = tmp_path / "project-doc.md"
    task_path = tmp_path / "task.txt"
    doc_path.write_text("# Project\n", encoding="utf-8")
    task_path.write_text("Create the project.\n", encoding="utf-8")

    try:
        main.main(
            [
                "--env-file",
                str(env_file),
                "--prjdir",
                str(workspace),
                "--docpath",
                str(doc_path),
                str(task_path),
            ]
        )
    except SystemExit as exc:
        assert "FRONTEND_VISION_MODEL" in str(exc)
    else:
        raise AssertionError("missing provider value should not be backfilled")


def test_keyboard_interrupt_reports_short_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "provider/vision")
    monkeypatch.setenv("CODE_EXECUTOR", "host")

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
    lg_agent_module.CodeExecutionConfig = lambda **kwargs: kwargs

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
