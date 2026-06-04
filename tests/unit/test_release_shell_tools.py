import types

import lg_tools


def test_shell_exec_uses_explicit_shell_without_python_shell_flag(monkeypatch):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["kwargs"] = kwargs
        return types.SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(lg_tools.platform, "system", lambda: "Linux")
    monkeypatch.setattr(lg_tools.subprocess, "run", fake_run)

    result = lg_tools.shell_exec.func("printf ok")

    assert result == "ok"
    assert calls["cmd"] == ["sh", "-lc", "printf ok"]
    assert calls["kwargs"].get("shell") is not True
