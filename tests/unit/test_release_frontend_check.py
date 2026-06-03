import subprocess

from frontend_check import FrontendChecker


class DummyProcess:
    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


def _set_provider_env(monkeypatch, api_key="test-key"):
    if api_key is None:
        monkeypatch.delenv("API_KEY", raising=False)
    else:
        monkeypatch.setenv("API_KEY", api_key)
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    monkeypatch.setenv("FRONTEND_VISION_MODEL", "provider/vision")


def test_frontend_checker_allows_explicit_api_key(monkeypatch):
    _set_provider_env(monkeypatch, api_key=None)

    checker = FrontendChecker(api_key="override-key")

    assert checker.api_key == "override-key"


def test_start_dev_server_does_not_use_shell(tmp_path, monkeypatch):
    _set_provider_env(monkeypatch)
    frontend_path = tmp_path / "frontend"
    frontend_path.mkdir()
    (frontend_path / "package.json").write_text("{}", encoding="utf-8")
    calls = []

    def fake_popen(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return DummyProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        FrontendChecker,
        "_wait_for_server",
        lambda self, port: True,
        raising=False,
    )

    checker = FrontendChecker(api_key="test-key")

    assert checker.start_dev_server(frontend_path, 5173)
    assert calls[0][0] == ["npm", "run", "dev", "--", "--port", "5173"]
    assert calls[0][1].get("shell") is not True


def test_start_dev_server_fails_when_server_never_becomes_ready(
    tmp_path, monkeypatch
):
    _set_provider_env(monkeypatch)
    frontend_path = tmp_path / "frontend"
    frontend_path.mkdir()
    (frontend_path / "package.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: DummyProcess())
    monkeypatch.setattr(
        FrontendChecker,
        "_wait_for_server",
        lambda self, port: False,
        raising=False,
    )

    checker = FrontendChecker(api_key="test-key")

    assert not checker.start_dev_server(frontend_path, 5173)
