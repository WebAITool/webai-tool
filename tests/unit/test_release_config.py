import importlib
import importlib.util
import os
import subprocess
import sys
import tomllib
from pathlib import Path


def test_load_llm_config_reads_openai_compatible_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "provider/vision")

    import llm_config

    importlib.reload(llm_config)
    config = llm_config.load_llm_config()

    assert config.api_key == "test-key"
    assert config.api_base_url == "https://example.test/v1"
    assert config.model == "provider/model"
    assert config.frontend_vision_model == "provider/vision"
    assert config.streaming is True
    assert config.stream_fallback_to_non_stream is True
    assert config.max_retries == 1
    assert config.connect_timeout_seconds == 10.0
    assert config.read_timeout_seconds is None
    assert config.write_timeout_seconds == 30.0
    assert config.pool_timeout_seconds == 30.0


def test_load_llm_config_reads_transport_settings(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "provider/vision")
    monkeypatch.setenv("LLM_STREAMING", "false")
    monkeypatch.setenv("LLM_STREAM_FALLBACK_TO_NON_STREAM", "false")
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")
    monkeypatch.setenv("LLM_CONNECT_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("LLM_READ_TIMEOUT_SECONDS", "42")
    monkeypatch.setenv("LLM_WRITE_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("LLM_POOL_TIMEOUT_SECONDS", "8")

    import llm_config

    importlib.reload(llm_config)
    config = llm_config.load_llm_config()

    assert config.streaming is False
    assert config.stream_fallback_to_non_stream is False
    assert config.max_retries == 4
    assert config.connect_timeout_seconds == 3.5
    assert config.read_timeout_seconds == 42.0
    assert config.write_timeout_seconds == 7.0
    assert config.pool_timeout_seconds == 8.0


def test_load_llm_config_disables_read_timeout_with_zero(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "provider/vision")
    monkeypatch.setenv("LLM_READ_TIMEOUT_SECONDS", "0")

    import llm_config

    importlib.reload(llm_config)
    config = llm_config.load_llm_config()

    assert config.read_timeout_seconds is None


def test_load_env_files_uses_explicit_file_as_isolated_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("FRONTEND_VISION_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "LLM_MODEL=provider/from-dotenv",
                "FRONTEND_VISION_MODEL=provider/vision-from-dotenv",
            ]
        ),
        encoding="utf-8",
    )
    env_file = tmp_path / "agent.env"
    env_file.write_text("export LLM_MODEL=provider/from-file\n", encoding="utf-8")

    import llm_config

    importlib.reload(llm_config)
    llm_config.load_env_files(str(env_file))

    assert os.environ["LLM_MODEL"] == "provider/from-file"
    assert "FRONTEND_VISION_MODEL" not in os.environ


def test_load_env_files_without_explicit_file_loads_dotenv_fallback(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "LLM_MODEL=provider/from-dotenv\n",
        encoding="utf-8",
    )

    import llm_config

    importlib.reload(llm_config)
    llm_config.load_env_files()

    assert os.environ["LLM_MODEL"] == "provider/from-dotenv"


def test_load_llm_config_can_skip_dotenv_loading(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("FRONTEND_VISION_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "API_KEY=dotenv-key",
                "LLM_API_BASE_URL=https://example.test/v1",
                "LLM_MODEL=provider/from-dotenv",
                "FRONTEND_VISION_MODEL=provider/vision-from-dotenv",
            ]
        ),
        encoding="utf-8",
    )

    import llm_config

    importlib.reload(llm_config)
    config = llm_config.load_llm_config(load_dotenv=False)

    assert config.api_key is None
    assert config.api_base_url is None
    assert config.model is None
    assert config.frontend_vision_model is None


def test_validate_llm_config_names_missing_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "provider/vision")

    import llm_config

    importlib.reload(llm_config)
    config = llm_config.load_llm_config()

    try:
        llm_config.validate_llm_config(config)
    except SystemExit as exc:
        assert "API_KEY" in str(exc)
    else:
        raise AssertionError("validate_llm_config should fail without API_KEY")


def test_validate_llm_config_requires_provider_routing(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "")
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "")

    import llm_config

    importlib.reload(llm_config)
    config = llm_config.load_llm_config()

    try:
        llm_config.validate_llm_config(config)
    except SystemExit as exc:
        message = str(exc)
        assert "LLM_API_BASE_URL" in message
        assert "LLM_MODEL" in message
        assert "FRONTEND_VISION_MODEL" in message
    else:
        raise AssertionError("validate_llm_config should fail without routing env")


def test_interactive_prompt_dependency_is_declared():
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    dependencies = pyproject["project"]["dependencies"]

    assert any(dep.startswith("rich") for dep in dependencies)
    assert any(dep.startswith("prompt-toolkit") for dep in dependencies)
    assert any(dep.startswith("httpx") for dep in dependencies)


def test_rich_prompt_imports_with_release_pythonpath():
    import sys

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "src"))
    try:
        from ui.prompt import ask

        assert callable(ask)
    finally:
        sys.path.remove(str(root / "src"))


def test_env_example_documents_required_provider_settings():
    root = Path(__file__).resolve().parents[2]
    content = (root / ".env.example").read_text(encoding="utf-8")

    assert "API_KEY=" in content
    assert "LLM_API_BASE_URL=" in content
    assert "LLM_MODEL=" in content
    assert "FRONTEND_VISION_MODEL=" in content
    assert "LLM_STREAMING=" in content
    assert "LLM_STREAM_FALLBACK_TO_NON_STREAM=" in content
    assert "LLM_READ_TIMEOUT_SECONDS=" in content
    assert "LLM_MAX_RETRIES=" in content
    assert "CODE_EXECUTOR_IMAGE=" in content
    assert "CODE_EXECUTOR_TIMEOUT_SECONDS=" in content
    assert "CODE_EXECUTOR_OUTPUT_LIMIT_BYTES=" in content
    assert "CODE_EXECUTOR_MEMORY=" in content
    assert "CODE_EXECUTOR_CPUS=" in content
    assert "CODE_EXECUTOR_PIDS_LIMIT=" in content
    assert "sk-or-" + "v1-" not in content


def test_tracked_files_do_not_contain_openrouter_secret_prefix():
    root = Path(__file__).resolve().parents[2]
    secret_prefix = "sk-or-" + "v1-"
    tracked_files = subprocess.check_output(
        ["git", "ls-files"],
        cwd=root,
        text=True,
    ).splitlines()

    for relative_path in tracked_files:
        path = root / relative_path
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert secret_prefix not in content, f"secret-like token in {relative_path}"


def test_transport_probe_rejects_missing_env_file(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    module_path = root / "scripts" / "llm_transport_probe.py"
    spec = importlib.util.spec_from_file_location("llm_transport_probe_test", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "llm_transport_probe.py",
            "--env-file",
            str(tmp_path / "missing.env"),
        ],
    )

    try:
        module.parse_args()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("missing probe --env-file should fail at parse time")
