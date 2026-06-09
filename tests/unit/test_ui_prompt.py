import importlib
import sys
import types


def _load_prompt_module(monkeypatch, prompt_impl):
    prompt_toolkit = types.ModuleType("prompt_toolkit")

    class PromptSession:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def prompt(self):
            return prompt_impl()

    prompt_toolkit.PromptSession = PromptSession
    prompt_toolkit.HTML = lambda text: text

    key_binding_module = types.ModuleType("prompt_toolkit.key_binding")

    class KeyBindings:
        def __init__(self):
            self.bindings = []

        def add(self, *keys):
            def decorator(func):
                self.bindings.append((keys, func))
                return func

            return decorator

    key_binding_module.KeyBindings = KeyBindings

    patch_stdout_module = types.ModuleType("prompt_toolkit.patch_stdout")

    class patch_stdout:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    patch_stdout_module.patch_stdout = patch_stdout

    monkeypatch.setitem(sys.modules, "prompt_toolkit", prompt_toolkit)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.key_binding", key_binding_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.patch_stdout", patch_stdout_module)

    import ui.prompt

    return importlib.reload(ui.prompt)


def test_ask_returns_multiline_prompt_text(monkeypatch):
    prompt = _load_prompt_module(monkeypatch, lambda: "line 1\nline 2")

    assert prompt.ask("Feedback") == "line 1\nline 2"


def test_ask_returns_empty_string_on_keyboard_interrupt(monkeypatch):
    def raise_interrupt():
        raise KeyboardInterrupt

    prompt = _load_prompt_module(monkeypatch, raise_interrupt)

    assert prompt.ask("Feedback") == ""
