import importlib
import subprocess
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

    class RecordingStateGraph:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.nodes = {}
            self.entry_point = None
            self.conditional_edges = []
            self.edges = []

        def add_node(self, name, node):
            self.nodes[name] = node

        def set_entry_point(self, name):
            self.entry_point = name

        def add_conditional_edges(self, source, path):
            self.conditional_edges.append((source, path))

        def add_edge(self, source, target):
            self.edges.append((source, target))

        def compile(self):
            return self

    graph_module.StateGraph = RecordingStateGraph
    monkeypatch.setitem(sys.modules, "langgraph", types.ModuleType("langgraph"))
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph_module)
    import lg_agent

    return importlib.reload(lg_agent)


def test_create_llm_uses_resolved_openai_compatible_config(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    config = lg_agent.LLMConfig(
        api_key="resolved-key",
        api_base_url="https://resolved.example/v1",
        model="provider/resolved-model",
        frontend_vision_model="provider/vision",
    )

    llm = lg_agent.create_llm(config)

    assert llm.kwargs == {
        "model_name": "provider/resolved-model",
        "base_url": "https://resolved.example/v1",
        "temperature": 0.3,
        "api_key": "resolved-key",
    }


def test_create_agent_wires_release_graph_nodes(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    config = lg_agent.LLMConfig(
        api_key="test-key",
        api_base_url="https://example.test/v1",
        model="provider/model",
        frontend_vision_model="provider/vision",
    )

    graph = lg_agent.create_agent(llm_config=config)

    assert set(graph.nodes) == {
        "thinker",
        "implementor",
        "execute_code",
        "verify_completion",
    }
    assert graph.entry_point == "thinker"
    assert ("implementor", "execute_code") in graph.edges
    assert [source for source, _ in graph.conditional_edges] == [
        "thinker",
        "execute_code",
        "verify_completion",
    ]


def test_create_agent_adds_interactive_feedback_node_only_when_enabled(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    config = lg_agent.LLMConfig(
        api_key="test-key",
        api_base_url="https://example.test/v1",
        model="provider/model",
        frontend_vision_model="provider/vision",
    )

    default_graph = lg_agent.create_agent(llm_config=config)
    interactive_graph = lg_agent.create_agent(interactive=True, llm_config=config)

    assert "ask_user" not in default_graph.nodes
    assert "ask_user" in interactive_graph.nodes
    assert [source for source, _ in interactive_graph.conditional_edges] == [
        "thinker",
        "execute_code",
        "verify_completion",
        "ask_user",
    ]


def test_commit_command_requires_commits_enabled(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["human_feedbacks"] = ["/commit"]

    route = lg_agent.make_route_after_answer(commits_enabled=False)

    assert route(state) == "ask_user"


def test_ask_user_records_feedback_and_resets_completion_state(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    ui_module = types.ModuleType("ui")
    ui_module.ask = lambda prompt="Your feedback": "add another line"
    monkeypatch.setitem(sys.modules, "ui", ui_module)

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["current_plan"] = "[CONFIRMED_DONE]"
    state["completion_failures"] = 2

    update = lg_agent.make_ask_user()(state)

    assert update["human_feedbacks"] == ["add another line"]
    assert update["current_plan"] == ""
    assert update["completion_failures"] == 0


def test_verify_completion_includes_actionable_feedback(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    verifier = lg_agent.make_verify_completion(object())
    captured = {}
    state = lg_agent.get_initial_state(goal="Create RESULT.txt", spec="", prjdir="/tmp/project")
    state["human_feedbacks"] = [
        "/commit",
        "append SUPER OK to RESULT.txt",
    ]

    def fake_invoke(llm, system_prompt, user_prompt):
        captured["user_prompt"] = user_prompt
        return "YES"

    monkeypatch.setattr(lg_agent, "invoke_text", fake_invoke)

    update = verifier(state)

    assert update["current_plan"] == "[CONFIRMED_DONE]"
    assert update["completion_failures"] == 0
    assert "/commit" not in captured["user_prompt"]
    assert "append SUPER OK to RESULT.txt" in captured["user_prompt"]


def test_route_after_verification_returns_to_feedback_after_repeated_failures(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["completion_failures"] = lg_agent.MAX_COMPLETION_FAILURES

    route = lg_agent.make_route_after_verification(interactive=True)

    assert route(state) == "ask_user"


def test_commit_command_uses_preview_and_prompt_message(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    calls = []

    git_module = types.SimpleNamespace(
        get_dirty_files=lambda: ["RESULT.txt"],
        commit=lambda files, message: calls.append((files, message)),
    )
    dev_env_module = types.ModuleType("dev_env")
    dev_env_module.git = git_module
    monkeypatch.setitem(sys.modules, "dev_env", dev_env_module)
    monkeypatch.setattr(
        lg_agent,
        "get_commit_preview",
        lambda prjdir, files: "diff --git a/RESULT.txt b/RESULT.txt",
    )
    monkeypatch.setattr(lg_agent.Prompt, "ask", lambda *args, **kwargs: "1")
    ui_module = types.ModuleType("ui")
    ui_module.ask = lambda prompt="Your feedback": "Add result"
    monkeypatch.setitem(sys.modules, "ui", ui_module)

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["human_feedbacks"] = ["/commit"]

    route = lg_agent.make_route_after_answer(commits_enabled=True)

    assert route(state) == "ask_user"
    assert calls == [(["RESULT.txt"], "Add result")]


def test_commit_command_can_generate_ai_message(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    calls = []

    git_module = types.SimpleNamespace(
        get_dirty_files=lambda: ["RESULT.txt"],
        commit=lambda files, message: calls.append((files, message)),
    )
    dev_env_module = types.ModuleType("dev_env")
    dev_env_module.git = git_module
    monkeypatch.setitem(sys.modules, "dev_env", dev_env_module)
    monkeypatch.setattr(
        lg_agent,
        "get_commit_preview",
        lambda prjdir, files: "diff --git a/RESULT.txt b/RESULT.txt",
    )
    monkeypatch.setattr(lg_agent.Prompt, "ask", lambda *args, **kwargs: "2")
    monkeypatch.setattr(
        lg_agent,
        "generate_commit_message",
        lambda llm, preview: "Add result file",
    )

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["human_feedbacks"] = ["/commit"]

    route = lg_agent.make_route_after_answer(
        commits_enabled=True,
        llm=object(),
    )

    assert route(state) == "ask_user"
    assert calls == [(["RESULT.txt"], "Add result file")]


def test_commit_preview_includes_untracked_file_diff(tmp_path, monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "RESULT.txt").write_text("OK\n", encoding="utf-8")

    preview = lg_agent.get_commit_preview(str(tmp_path), ["RESULT.txt"])

    assert "?? RESULT.txt" in preview
    assert "+OK" in preview


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


def test_execute_python_code_uses_current_interpreter(tmp_path, monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(lg_agent.subprocess, "run", fake_run)

    result = lg_agent.execute_python_code("print('ok')", str(tmp_path))

    assert result.success
    assert calls[0][0][0] == sys.executable


def test_route_after_thinker_accepts_done_marker_with_extra_text(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["current_plan"] = "The task is complete.\n[DONE]"

    assert lg_agent.route_after_thinker(state) == "verify_completion"


def test_verify_completion_accepts_yes_inside_model_explanation(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    verifier = lg_agent.make_verify_completion(object())
    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")

    monkeypatch.setattr(lg_agent, "invoke_text", lambda *args: "Yes, it is done.")

    update = verifier(state)

    assert update["current_plan"] == "[CONFIRMED_DONE]"
    assert update["completion_failures"] == 0


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
