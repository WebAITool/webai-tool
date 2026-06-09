import importlib
import subprocess
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
