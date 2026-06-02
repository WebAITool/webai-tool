import importlib
import sys
import types


def _load_lg_agent(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "provider/model")
    messages_module = types.ModuleType("langchain_core.messages")
    messages_module.HumanMessage = lambda content: ("human", content)
    messages_module.SystemMessage = lambda content: ("system", content)
    monkeypatch.setitem(sys.modules, "langchain_core", types.ModuleType("langchain_core"))
    monkeypatch.setitem(sys.modules, "langchain_core.messages", messages_module)

    openai_module = types.ModuleType("langchain_openai")

    class ChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    openai_module.ChatOpenAI = ChatOpenAI
    monkeypatch.setitem(sys.modules, "langchain_openai", openai_module)

    graph_module = types.ModuleType("langgraph.graph")
    graph_module.END = "__end__"

    class StateGraph:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def add_node(self, *args, **kwargs):
            pass

        def set_entry_point(self, *args, **kwargs):
            pass

        def add_conditional_edges(self, *args, **kwargs):
            pass

        def add_edge(self, *args, **kwargs):
            pass

        def compile(self):
            return self

    graph_module.StateGraph = StateGraph
    monkeypatch.setitem(sys.modules, "langgraph", types.ModuleType("langgraph"))
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph_module)
    import lg_agent

    return importlib.reload(lg_agent)


def test_extract_code_selects_python_block(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    text = """First try:
```bash
python backend/app.py
```

Correct implementation:
```python
print("ok")
```
"""

    assert lg_agent.extract_code(text) == 'print("ok")'


def test_extract_code_keeps_markdown_fences_inside_python_string(
    tmp_path, monkeypatch
):
    lg_agent = _load_lg_agent(monkeypatch)

    text = '''Implementation:
```python
from pathlib import Path

readme_content = """# Backend

```sh
python backend/app.py --check
```
"""

Path("README.md").write_text(readme_content, encoding="utf-8")
```
'''

    code = lg_agent.extract_code(text)
    compile(code, "<agent-code>", "exec")

    result = lg_agent.execute_python_code(code, str(tmp_path))

    assert result.success, result.stderr
    assert "```sh" in (tmp_path / "README.md").read_text(encoding="utf-8")


def test_extract_code_rejects_non_python_fenced_blocks(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    code = lg_agent.extract_code(
        """```bash
print("this is not trusted python")
```"""
    )

    assert code.startswith("raise RuntimeError")
    assert "python fenced code block" in code


def test_execute_code_records_failure_after_retry_exhaustion(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    monkeypatch.setattr(
        lg_agent,
        "execute_python_code",
        lambda code, prjdir: lg_agent.ExecutionResult(
            success=False,
            returncode=1,
            stdout="",
            stderr="SyntaxError: bad code",
        ),
    )
    state = lg_agent.get_initial_state(
        goal="create backend",
        spec="",
        prjdir="/tmp/project",
    )
    state["current_plan"] = "Write the backend app."
    state["current_code"] = "bad code"
    state["implementor_retries"] = 2

    update = lg_agent.execute_code(state)

    assert update["implementor_retries"] == 3
    assert "chat_history" in update
    assert "SyntaxError: bad code" in update["chat_history"][-1]
    assert "Result: FAILURE" in update["chat_history"][-1]


def test_route_after_thinker_accepts_done_marker_with_extra_text(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["current_plan"] = "The task is complete.\n[DONE]"

    assert lg_agent.route_after_thinker(state) == "verify_completion"


def test_execute_python_code_captures_traceback_and_removes_script(
    tmp_path, monkeypatch
):
    lg_agent = _load_lg_agent(monkeypatch)

    result = lg_agent.execute_python_code(
        'raise RuntimeError("boom")',
        str(tmp_path),
    )

    assert not result.success
    assert result.returncode != 0
    assert "RuntimeError: boom" in result.stderr
    assert not (tmp_path / ".agent_script.py").exists()
