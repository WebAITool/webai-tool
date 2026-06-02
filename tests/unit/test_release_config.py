import importlib


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

    import llm_config

    importlib.reload(llm_config)
    config = llm_config.load_llm_config()

    try:
        llm_config.validate_llm_config(config)
    except SystemExit as exc:
        assert "API_KEY is required" in str(exc)
    else:
        raise AssertionError("validate_llm_config should fail without API_KEY")

