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
        streaming=True,
        stream_fallback_to_non_stream=True,
        max_retries=5,
        connect_timeout_seconds=1.0,
        read_timeout_seconds=2.0,
        write_timeout_seconds=3.0,
        pool_timeout_seconds=4.0,
    )

    llm = lg_agent.create_llm(config)

    assert llm.config is config
    assert llm.temperature == 0.3
    assert llm.timeout.connect == 1.0
    assert llm.timeout.read == 2.0
    assert llm.timeout.write == 3.0
    assert llm.timeout.pool == 4.0


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
    assert update["pending_feedback"] == "add another line"


def test_thinker_does_not_accept_done_when_feedback_is_pending(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    thinker = lg_agent.make_thinker(object())
    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["human_feedbacks"] = ["append SUPER OK to RESULT.txt"]
    state["pending_feedback"] = "append SUPER OK to RESULT.txt"

    monkeypatch.setattr(lg_agent, "make_tree", lambda prjdir: "(empty project)")
    monkeypatch.setattr(lg_agent, "invoke_text", lambda *args: "[DONE]")

    update = thinker(state)

    assert update["current_plan"] == (
        "Handle the latest user feedback before finishing:\n"
        "append SUPER OK to RESULT.txt"
    )
    assert lg_agent.route_after_thinker({**state, **update}) == "implementor"


def test_thinker_forces_initial_inspection_before_existing_file_edits(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    thinker = lg_agent.make_thinker(object())
    state = lg_agent.get_initial_state(goal="hash passwords", spec="", prjdir="/tmp/project")

    monkeypatch.setattr(
        lg_agent,
        "make_tree",
        lambda prjdir: "backend/schema.sql\nbackend/app/routes/auth.py",
    )
    monkeypatch.setattr(
        lg_agent,
        "invoke_text",
        lambda *args: (
            "Modify backend/schema.sql and backend/app/routes/auth.py to use bcrypt."
        ),
    )

    update = thinker(state)

    assert update["current_plan"].startswith(
        "Inspect the smallest relevant snippets before editing."
    )
    assert "backend/schema.sql" in update["current_plan"]
    assert "backend/app/routes/auth.py" in update["current_plan"]


def test_initial_inspection_guard_keeps_new_file_plan(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    state = lg_agent.get_initial_state(goal="create result", spec="", prjdir="/tmp/project")

    plan = lg_agent.force_initial_inspection_for_existing_file_edits(
        "Create RESULT.txt with OK.",
        state,
    )

    assert plan == "Create RESULT.txt with OK."


def test_implementor_uses_llm_for_inspection_plans(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    captured = {}

    class InspectLLM:
        def invoke(self, messages):
            captured["messages"] = messages
            return types.SimpleNamespace(
                content=(
                    "```python\n"
                    "from pathlib import Path\n"
                    "print(Path('backend/schema.sql').read_text())\n"
                    "```"
                )
            )

    monkeypatch.setattr(lg_agent, "make_tree", lambda prjdir: "backend/schema.sql")
    state = lg_agent.get_initial_state(goal="inspect", spec="", prjdir="/tmp/project")
    state["current_plan"] = "Read backend/schema.sql snippets."
    implementor = lg_agent.make_implementor(InspectLLM())

    update = implementor(state)

    assert "backend/schema.sql" in update["current_code"]
    assert "messages" in captured


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


def test_commit_preview_filters_sensitive_env_paths(tmp_path, monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "RESULT.txt").write_text("OK\n", encoding="utf-8")
    (tmp_path / ".envrc").write_text("API_KEY=secret\n", encoding="utf-8")

    preview = lg_agent.get_commit_preview(str(tmp_path), ["RESULT.txt", ".envrc"])

    assert "RESULT.txt" in preview
    assert ".envrc" not in preview
    assert "secret" not in preview


def test_post_execution_git_diff_filters_tracked_env_changes(tmp_path, monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    from dev_env import git as git_module

    monkeypatch.setattr(git_module, "_is_initialized", False)
    (tmp_path / ".gitignore").write_text("custom.log\n", encoding="utf-8")
    git_module.init_git(tmp_path, "dev")
    (tmp_path / ".gitignore").write_text("custom.log\n", encoding="utf-8")
    (tmp_path / ".env.polza").write_text("API_KEY=old\n", encoding="utf-8")
    (tmp_path / "RESULT.txt").write_text("OK\n", encoding="utf-8")
    git_module._REPO.git.add("-f", ".env.polza")
    git_module._REPO.git.add("RESULT.txt")
    git_module._REPO.index.commit("seed", author=git_module._AGENT_ACTOR)

    (tmp_path / ".env.polza").write_text("API_KEY=secret\n", encoding="utf-8")
    (tmp_path / "RESULT.txt").write_text("OK\nSUPER OK\n", encoding="utf-8")

    diff = lg_agent.get_git_diff(str(tmp_path))

    assert "RESULT.txt" in diff
    assert ".env.polza" not in diff
    assert "secret" not in diff


def test_post_execution_git_diff_works_without_commit_mode(tmp_path, monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    from dev_env import git as git_module

    monkeypatch.setattr(git_module, "_is_initialized", False)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / "RESULT.txt").write_text("OK\n", encoding="utf-8")
    subprocess.run(["git", "add", "RESULT.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True)
    (tmp_path / "RESULT.txt").write_text("OK\nSUPER OK\n", encoding="utf-8")

    diff = lg_agent.get_git_diff(str(tmp_path))

    assert "RESULT.txt" in diff
    assert "+SUPER OK" in diff


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
        lambda code, prjdir, **kwargs: lg_agent.ExecutionResult(
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


def test_execute_code_clears_pending_feedback_after_success(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    monkeypatch.setattr(
        lg_agent,
        "execute_python_code",
        lambda code, prjdir, **kwargs: lg_agent.ExecutionResult(
            success=True,
            returncode=0,
            stdout="",
            stderr="",
        ),
    )
    state = lg_agent.get_initial_state(
        goal="create result",
        spec="",
        prjdir="/tmp/project",
    )
    state["current_plan"] = "Append SUPER OK."
    state["current_code"] = "pass"
    state["pending_feedback"] = "append SUPER OK"

    update = lg_agent.execute_code(state)

    assert update["pending_feedback"] == ""


def test_execute_code_compacts_large_stdout_in_history(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    long_stdout = "A" * 5000 + "KEEP_TAIL"

    monkeypatch.setattr(
        lg_agent,
        "execute_python_code",
        lambda code, prjdir, **kwargs: lg_agent.ExecutionResult(
            success=True,
            returncode=0,
            stdout=long_stdout,
            stderr="",
        ),
    )
    state = lg_agent.get_initial_state(
        goal="inspect files",
        spec="",
        prjdir="/tmp/project",
    )
    state["current_plan"] = "Read a large file."
    state["current_code"] = "pass"

    update = lg_agent.execute_code(state)

    history_entry = update["chat_history"][-1]
    assert len(history_entry) <= lg_agent.HISTORY_ENTRY_LIMIT
    assert "truncated" in history_entry
    assert "KEEP_TAIL" in history_entry


def test_format_history_compacts_total_history(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    history = ["A" * 8000, "B" * 8000]

    formatted = lg_agent.format_history(history)

    assert len(formatted) <= lg_agent.HISTORY_TOTAL_LIMIT
    assert "truncated" in formatted


def test_openai_compatible_client_falls_back_to_non_stream(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    from llm_client import LLMTransportError, OpenAICompatibleChatClient

    config = lg_agent.LLMConfig(
        api_key="key",
        api_base_url="https://example.test/v1",
        model="provider/model",
        frontend_vision_model="provider/vision",
        streaming=True,
        stream_fallback_to_non_stream=True,
        max_retries=0,
    )
    client = OpenAICompatibleChatClient(config)
    calls = []

    def fail_stream(messages, attempt):
        calls.append(("stream", attempt))
        raise LLMTransportError("no content")

    def pass_non_stream(messages, attempt):
        calls.append(("non-stream", attempt))
        return "OK"

    monkeypatch.setattr(client, "_invoke_stream", fail_stream)
    monkeypatch.setattr(client, "_invoke_non_stream", pass_non_stream)

    response = client.invoke([])

    assert response.content == "OK"
    assert calls == [("stream", 1), ("non-stream", 1)]


def test_openai_compatible_client_wraps_malformed_json(monkeypatch):
    _load_lg_agent(monkeypatch)
    from llm_client import LLMTransportError, _load_json

    try:
        _load_json("{not-json", "stream response chunk")
    except LLMTransportError as exc:
        assert "Malformed JSON" in str(exc)
        assert "stream response chunk" in str(exc)
    else:
        raise AssertionError("Malformed JSON should be an LLMTransportError")


def test_implementor_turns_transport_failure_into_retryable_code(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    from llm_client import LLMTransportError

    class FailingLLM:
        def invoke(self, messages):
            raise LLMTransportError("body stalled")

    monkeypatch.setattr(lg_agent, "make_tree", lambda prjdir: "project/")
    implementor = lg_agent.make_implementor(FailingLLM())
    state = lg_agent.get_initial_state(
        goal="change file",
        spec="",
        prjdir="/tmp/project",
    )
    state["current_plan"] = "Edit RESULT.txt"

    update = implementor(state)

    assert update["current_code"].startswith("raise RuntimeError")
    assert "LLM transport failed" in update["current_code"]


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


def test_execute_python_code_can_use_docker_executor(tmp_path, monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(lg_agent, "run_capped_subprocess", fake_run)

    result = lg_agent.execute_python_code(
        "print('ok')",
        str(tmp_path),
        executor="docker",
        docker_image="webai-tool:test",
        docker_network="none",
    )

    assert result.success
    assert result.stdout == "ok"
    cmd = calls[0][0]
    assert cmd[:3] == ["docker", "run", "--rm"]
    assert "--network" in cmd
    assert cmd[cmd.index("--network") + 1] == "none"
    assert "--read-only" in cmd
    assert "--cap-drop" in cmd
    assert "ALL" == cmd[cmd.index("--cap-drop") + 1]
    assert "--security-opt" in cmd
    assert "no-new-privileges" == cmd[cmd.index("--security-opt") + 1]
    assert "--memory" in cmd
    assert "4g" == cmd[cmd.index("--memory") + 1]
    assert "--cpus" in cmd
    assert "4" == cmd[cmd.index("--cpus") + 1]
    assert "--pids-limit" in cmd
    assert "512" == cmd[cmd.index("--pids-limit") + 1]
    assert "--entrypoint" in cmd
    assert "python" == cmd[cmd.index("--entrypoint") + 1]
    assert "--mount" in cmd
    assert f"type=bind,src={tmp_path},dst=/workspace/project" in cmd
    assert "-w" in cmd
    assert "/workspace/project" in cmd
    assert "webai-tool:test" in cmd
    assert cmd[-2:] == ["webai-tool:test", ".agent_script.py"]
    if hasattr(lg_agent.os, "getuid") and hasattr(lg_agent.os, "getgid"):
        assert "--user" in cmd
        assert f"{lg_agent.os.getuid()}:{lg_agent.os.getgid()}" in cmd
    assert not (tmp_path / ".agent_script.py").exists()


def test_docker_executor_requires_explicit_image(tmp_path, monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    result = lg_agent.execute_python_code(
        "print('ok')",
        str(tmp_path),
        executor="docker",
        docker_image="",
    )

    assert not result.success
    assert result.returncode == 2
    assert "requires --code-executor-image" in result.stderr
    assert not (tmp_path / ".agent_script.py").exists()


def test_docker_executor_maps_host_project_path_to_container_path(
    tmp_path, monkeypatch
):
    lg_agent = _load_lg_agent(monkeypatch)
    captured = {}
    code = (
        "from pathlib import Path\n"
        f"Path({str(tmp_path / 'RESULT.txt')!r}).write_text('OK')\n"
    )

    def fake_execute(prjdir, script_name, docker_image, docker_network, **kwargs):
        captured["code"] = (tmp_path / script_name).read_text(encoding="utf-8")
        return subprocess.CompletedProcess(
            ["docker"],
            0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(lg_agent, "execute_python_code_in_docker", fake_execute)

    result = lg_agent.execute_python_code(
        code,
        str(tmp_path),
        executor="docker",
        docker_image="webai-tool:test",
    )

    assert result.success
    assert str(tmp_path) not in captured["code"]
    assert lg_agent.DOCKER_EXECUTOR_PROJECT_DIR in captured["code"]
    assert not (tmp_path / ".agent_script.py").exists()


def test_docker_executor_times_out_and_caps_output(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)
    calls = []
    callbacks = []

    class FakeProcess:
        def __init__(self):
            self.waits = 0

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired(["docker"], timeout)
            return 124

        def kill(self):
            calls.append("kill")

    def fake_popen(cmd, **kwargs):
        stdout = kwargs["stdout"]
        stderr = kwargs["stderr"]
        stdout.write(b"A" * 20)
        stderr.write(b"B" * 20)
        stdout.flush()
        stderr.flush()
        return FakeProcess()

    monkeypatch.setattr(lg_agent.subprocess, "Popen", fake_popen)

    result = lg_agent.run_capped_subprocess(
        ["docker"],
        timeout_seconds=1,
        output_limit_bytes=5,
        on_timeout=lambda: callbacks.append("cleanup"),
    )

    assert result.returncode == 124
    assert "AAAAA" in result.stdout
    assert "truncated after 5 bytes" in result.stdout
    assert "Execution timed out after 1s." in result.stderr
    assert calls == ["kill"]
    assert callbacks == ["cleanup"]


def test_get_initial_state_records_code_execution_config(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    state = lg_agent.get_initial_state(
        goal="change project",
        prjdir="/tmp/project",
        code_execution=lg_agent.CodeExecutionConfig(
            executor="docker",
            docker_image="webai-tool:test",
            docker_network="bridge",
        ),
    )

    assert state["code_executor"] == "docker"
    assert state["code_executor_image"] == "webai-tool:test"
    assert state["code_executor_network"] == "bridge"
    assert state["code_executor_timeout_seconds"] == lg_agent.DEFAULT_CODE_EXECUTOR_TIMEOUT_SECONDS
    assert state["code_executor_output_limit_bytes"] == lg_agent.DEFAULT_CODE_EXECUTOR_OUTPUT_LIMIT_BYTES
    assert state["code_executor_memory"] == lg_agent.DEFAULT_CODE_EXECUTOR_MEMORY
    assert state["code_executor_cpus"] == lg_agent.DEFAULT_CODE_EXECUTOR_CPUS
    assert state["code_executor_pids_limit"] == lg_agent.DEFAULT_CODE_EXECUTOR_PIDS_LIMIT


def test_route_after_thinker_accepts_done_marker_with_extra_text(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["current_plan"] = "The task is complete.\n[DONE]"

    assert lg_agent.route_after_thinker(state) == "verify_completion"


def test_route_after_thinker_accepts_done_marker_with_inner_spaces(monkeypatch):
    lg_agent = _load_lg_agent(monkeypatch)

    state = lg_agent.get_initial_state(goal="done", spec="", prjdir="/tmp/project")
    state["current_plan"] = "[ DONE ]"

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
