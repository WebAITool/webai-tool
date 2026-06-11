import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import List, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax

from llm_client import LLMTransportError, OpenAICompatibleChatClient
from llm_config import LLMConfig, load_llm_config, validate_llm_config


console = Console()
MAX_COMPLETION_FAILURES = 3
HISTORY_ENTRY_LIMIT = 4000
HISTORY_TOTAL_LIMIT = 12000
SCRIPT_OUTPUT_HISTORY_LIMIT = 3000
DOCKER_EXECUTOR_PROJECT_DIR = "/workspace/project"
DEFAULT_CODE_EXECUTOR_TIMEOUT_SECONDS = 600
DEFAULT_CODE_EXECUTOR_OUTPUT_LIMIT_BYTES = 4 * 1024 * 1024
DEFAULT_CODE_EXECUTOR_MEMORY = "4g"
DEFAULT_CODE_EXECUTOR_CPUS = "4"
DEFAULT_CODE_EXECUTOR_PIDS_LIMIT = 512
EDIT_PLAN_RE = re.compile(
    r"\b(modify|update|change|edit|refactor|fix|replace|hash|check)\b",
    flags=re.IGNORECASE,
)
INSPECTION_PLAN_RE = re.compile(
    r"\b(read|inspect|print|show|list)\b",
    flags=re.IGNORECASE,
)
FILE_PATH_RE = re.compile(
    r"[\w./-]+\.(?:py|sql|txt|md|json|toml|yaml|yml|js|ts|vue|html|css|env|ini|cfg)",
    flags=re.IGNORECASE,
)
CONTROL_FEEDBACK = {
    "",
    "/commit",
    "/exit",
    "/quit",
    "/q",
}

@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CodeExecutionConfig:
    executor: str = "host"
    docker_image: str = ""
    docker_network: str = "none"
    timeout_seconds: int = DEFAULT_CODE_EXECUTOR_TIMEOUT_SECONDS
    output_limit_bytes: int = DEFAULT_CODE_EXECUTOR_OUTPUT_LIMIT_BYTES
    memory: str = DEFAULT_CODE_EXECUTOR_MEMORY
    cpus: str = DEFAULT_CODE_EXECUTOR_CPUS
    pids_limit: int = DEFAULT_CODE_EXECUTOR_PIDS_LIMIT


class AgentState(TypedDict):
    goal: str
    prjdir: str
    code_executor: str
    code_executor_image: str
    code_executor_network: str
    code_executor_timeout_seconds: int
    code_executor_output_limit_bytes: int
    code_executor_memory: str
    code_executor_cpus: str
    code_executor_pids_limit: int
    chat_history: List[str]
    human_feedbacks: List[str]
    current_plan: str
    current_code: str
    last_error: str
    implementor_retries: int
    iterations: int
    max_steps: int
    completion_failures: int
    pending_feedback: str


def create_llm(config: LLMConfig | None = None) -> OpenAICompatibleChatClient:
    if config is None:
        config = load_llm_config()
    validate_llm_config(config)
    return OpenAICompatibleChatClient(config, temperature=0.3)


def make_tree(prjpath: str) -> str:
    from repo_map import RepomapGenerator

    return RepomapGenerator().get_map(prjpath, ensure_gitignore=False)


def _is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def _find_unescaped(text: str, needle: str, start: int = 0) -> int:
    cursor = start
    while True:
        index = text.find(needle, cursor)
        if index == -1 or not _is_escaped(text, index):
            return index
        cursor = index + len(needle)


def _next_triple_quote(text: str, start: int = 0) -> tuple[int, str] | None:
    candidates = []
    for delimiter in ('"""', "'''"):
        index = _find_unescaped(text, delimiter, start)
        if index != -1:
            candidates.append((index, delimiter))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])


def _update_triple_quote_state(line: str, delimiter: str | None) -> str | None:
    cursor = 0
    while cursor < len(line):
        if delimiter:
            index = _find_unescaped(line, delimiter, cursor)
            if index == -1:
                return delimiter
            delimiter = None
            cursor = index + 3
            continue

        next_quote = _next_triple_quote(line, cursor)
        if next_quote is None:
            return None
        index, delimiter = next_quote
        cursor = index + 3
    return delimiter


def _iter_fenced_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    lines = text.splitlines(keepends=True)
    line_index = 0

    while line_index < len(lines):
        stripped = lines[line_index].strip()
        if not stripped.startswith("```") or stripped == "```":
            line_index += 1
            continue

        language = stripped[3:].strip().split(maxsplit=1)[0].lower()
        is_python = language in {"python", "py"}
        triple_quote: str | None = None
        content: list[str] = []
        line_index += 1

        while line_index < len(lines):
            line = lines[line_index]
            if line.strip() == "```" and (not is_python or triple_quote is None):
                break

            content.append(line)
            if is_python:
                triple_quote = _update_triple_quote_state(line, triple_quote)
            line_index += 1

        blocks.append((language, "".join(content)))
        line_index += 1

    return blocks


def extract_code(text: str) -> str:
    if "```" not in text:
        return text.strip()

    for language, block in _iter_fenced_blocks(text):
        stripped = block.strip()
        if not stripped:
            continue
        if language in {"python", "py"}:
            return stripped
    return (
        "raise RuntimeError("
        "'Implementor response did not contain a python fenced code block'"
        ")"
    )


def execute_python_code(
    code: str,
    prjdir: str,
    executor: str = "host",
    docker_image: str = "",
    docker_network: str = "none",
    timeout_seconds: int = DEFAULT_CODE_EXECUTOR_TIMEOUT_SECONDS,
    output_limit_bytes: int = DEFAULT_CODE_EXECUTOR_OUTPUT_LIMIT_BYTES,
    memory: str = DEFAULT_CODE_EXECUTOR_MEMORY,
    cpus: str = DEFAULT_CODE_EXECUTOR_CPUS,
    pids_limit: int = DEFAULT_CODE_EXECUTOR_PIDS_LIMIT,
) -> ExecutionResult:
    temp_script_path = os.path.join(prjdir, ".agent_script.py")
    try:
        code_to_run = code
        if executor == "docker":
            code_to_run = map_host_project_paths_for_docker(code, prjdir)
        with open(temp_script_path, "w", encoding="utf-8") as file:
            file.write(code_to_run)

        if executor == "host":
            try:
                result = subprocess.run(
                    [sys.executable, ".agent_script.py"],
                    cwd=prjdir,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                result = subprocess.CompletedProcess(
                    [sys.executable, ".agent_script.py"],
                    124,
                    stdout=_timeout_output_to_text(exc.stdout),
                    stderr=(
                        _timeout_output_to_text(exc.stderr)
                        + f"\nExecution timed out after {timeout_seconds}s."
                    ).strip(),
                )
            result = cap_completed_process_output(result, output_limit_bytes)
        elif executor == "docker":
            if not docker_image:
                return ExecutionResult(
                    success=False,
                    returncode=2,
                    stdout="",
                    stderr=(
                        "Docker code executor requires --code-executor-image "
                        "or CODE_EXECUTOR_IMAGE."
                    ),
                )
            result = execute_python_code_in_docker(
                prjdir=prjdir,
                script_name=".agent_script.py",
                docker_image=docker_image,
                docker_network=docker_network,
                timeout_seconds=timeout_seconds,
                output_limit_bytes=output_limit_bytes,
                memory=memory,
                cpus=cpus,
                pids_limit=pids_limit,
            )
        else:
            return ExecutionResult(
                success=False,
                returncode=2,
                stdout="",
                stderr=f"Unknown code executor: {executor}",
            )
        return ExecutionResult(
            success=result.returncode == 0,
            returncode=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
        )
    finally:
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)


def execute_python_code_in_docker(
    prjdir: str,
    script_name: str,
    docker_image: str,
    docker_network: str,
    timeout_seconds: int,
    output_limit_bytes: int,
    memory: str,
    cpus: str,
    pids_limit: int,
) -> subprocess.CompletedProcess[str]:
    mount_target = DOCKER_EXECUTOR_PROJECT_DIR
    with tempfile.TemporaryDirectory(prefix="webai-docker-") as temp_dir:
        cidfile = os.path.join(temp_dir, "container.cid")
        cmd = [
            "docker",
            "run",
            "--rm",
            "--cidfile",
            cidfile,
            "--network",
            docker_network,
            "--entrypoint",
            "python",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=512m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            memory,
            "--cpus",
            cpus,
            "--pids-limit",
            str(pids_limit),
        ]
        if hasattr(os, "getuid") and hasattr(os, "getgid"):
            cmd.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
        cmd.extend(
            [
                "-e",
                "HOME=/tmp",
                "-e",
                "PYTHONDONTWRITEBYTECODE=1",
                "--mount",
                f"type=bind,src={os.path.abspath(prjdir)},dst={mount_target}",
                "-w",
                mount_target,
                docker_image,
                script_name,
            ]
        )

        def cleanup_container() -> None:
            try:
                with open(cidfile, "r", encoding="utf-8") as file:
                    container_id = file.read().strip()
            except OSError:
                return
            if not container_id:
                return
            try:
                subprocess.run(
                    ["docker", "rm", "-f", container_id],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except (OSError, subprocess.SubprocessError):
                logging.warning(
                    "Failed to force-remove timed-out Docker container %s",
                    container_id,
                )

        return run_capped_subprocess(
            cmd,
            timeout_seconds=timeout_seconds,
            output_limit_bytes=output_limit_bytes,
            on_timeout=cleanup_container,
        )


def run_capped_subprocess(
    cmd: list[str],
    cwd: str | None = None,
    timeout_seconds: int = DEFAULT_CODE_EXECUTOR_TIMEOUT_SECONDS,
    output_limit_bytes: int = DEFAULT_CODE_EXECUTOR_OUTPUT_LIMIT_BYTES,
    on_timeout=None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="webai-exec-") as temp_dir:
        stdout_path = os.path.join(temp_dir, "stdout")
        stderr_path = os.path.join(temp_dir, "stderr")
        try:
            with open(stdout_path, "wb") as stdout_file, open(
                stderr_path,
                "wb",
            ) as stderr_file:
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=stdout_file,
                    stderr=stderr_file,
                )
                try:
                    returncode = process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    if on_timeout is not None:
                        on_timeout()
                    process.kill()
                    process.wait()
                    return subprocess.CompletedProcess(
                        cmd,
                        124,
                        stdout=read_limited_text(stdout_path, output_limit_bytes),
                        stderr=(
                            read_limited_text(stderr_path, output_limit_bytes)
                            + f"\nExecution timed out after {timeout_seconds}s."
                        ).strip(),
                    )
        except FileNotFoundError as exc:
            executable = cmd[0] if cmd else "executable"
            return subprocess.CompletedProcess(
                cmd,
                127,
                stdout="",
                stderr=f"{executable} executable not found: {exc}",
            )
        return subprocess.CompletedProcess(
            cmd,
            returncode,
            stdout=read_limited_text(stdout_path, output_limit_bytes),
            stderr=read_limited_text(stderr_path, output_limit_bytes),
        )


def cap_completed_process_output(
    result: subprocess.CompletedProcess[str],
    output_limit_bytes: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        stdout=cap_text_bytes(result.stdout or "", output_limit_bytes),
        stderr=cap_text_bytes(result.stderr or "", output_limit_bytes),
    )


def read_limited_text(path: str, limit_bytes: int) -> str:
    try:
        with open(path, "rb") as file:
            data = file.read(max(limit_bytes, 0) + 1)
    except OSError:
        return ""
    return cap_bytes(data, limit_bytes)


def cap_text_bytes(text: str, limit_bytes: int) -> str:
    return cap_bytes(text.encode("utf-8", errors="replace"), limit_bytes)


def cap_bytes(data: bytes, limit_bytes: int) -> str:
    if limit_bytes <= 0:
        return ""
    truncated = len(data) > limit_bytes
    if truncated:
        data = data[:limit_bytes]
    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += f"\n[...output truncated after {limit_bytes} bytes...]"
    return text


def _timeout_output_to_text(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def map_host_project_paths_for_docker(code: str, prjdir: str) -> str:
    return code.replace(os.path.abspath(prjdir), DOCKER_EXECUTOR_PROJECT_DIR)


def format_history(history: List[str]) -> str:
    if not history:
        return "No actions taken yet."
    return compact_text("\n".join(history), HISTORY_TOTAL_LIMIT)


def compact_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    marker = (
        "\n\n[...truncated "
        f"{len(text) - max_chars} characters from the middle...]\n\n"
    )
    keep = max_chars - len(marker)
    if keep <= 0:
        return text[:max_chars]
    head = keep // 2
    tail = keep - head
    return text[:head] + marker + text[-tail:]


def compact_history_entry(entry: str) -> str:
    return compact_text(entry, HISTORY_ENTRY_LIMIT)


def is_control_feedback(feedback: str) -> bool:
    return feedback.strip() in CONTROL_FEEDBACK


def get_actionable_feedbacks(state: AgentState) -> list[str]:
    return [
        feedback.strip()
        for feedback in state.get("human_feedbacks", [])
        if feedback.strip() and not is_control_feedback(feedback)
    ]


def format_actionable_feedbacks(state: AgentState) -> str:
    feedbacks = get_actionable_feedbacks(state)
    if not feedbacks:
        return "No user feedback."
    return "\n\n".join(
        f"{index}. {feedback}"
        for index, feedback in enumerate(feedbacks, start=1)
    )


def has_done_marker(plan: str) -> bool:
    return re.search(r"\[\s*DONE\s*\]", plan, flags=re.IGNORECASE) is not None


def prevent_premature_done(plan: str, pending_feedback: str) -> str:
    if not pending_feedback or not has_done_marker(plan):
        return plan
    return (
        "Handle the latest user feedback before finishing:\n"
        f"{pending_feedback}"
    )


def force_initial_inspection_for_existing_file_edits(
    plan: str,
    state: AgentState,
) -> str:
    if state.get("chat_history"):
        return plan
    if INSPECTION_PLAN_RE.search(plan):
        return plan
    if not EDIT_PLAN_RE.search(plan):
        return plan
    if not FILE_PATH_RE.search(plan):
        return plan
    return (
        "Inspect the smallest relevant snippets before editing. "
        "Print the exact current lines or compact function/table snippets "
        "needed for this requested change, using project-relative paths only:\n"
        f"{plan}"
    )


def get_git_diff(prjdir: str) -> str:
    try:
        from dev_env.git import is_sensitive_env_path

        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=prjdir,
            capture_output=True,
            text=True,
        )
        if status.returncode != 0:
            return ""
        diff_files = []
        for line in status.stdout.splitlines():
            path_text = line[3:].strip()
            if " -> " in path_text:
                paths = path_text.split(" -> ", 1)
            else:
                paths = [path_text]
            for path in paths:
                if path and not is_sensitive_env_path(path):
                    diff_files.append(path)
        if not diff_files:
            return ""
        result = subprocess.run(
            ["git", "diff", "--no-color", "--", *diff_files],
            cwd=prjdir,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_commit_preview(prjdir: str, dirty_files: list[str]) -> str:
    from dev_env.git import is_sensitive_env_path

    preview_files: list[str] = []
    for file_path in dirty_files:
        if " -> " in file_path:
            old_path, new_path = file_path.split(" -> ", 1)
            if not (
                is_sensitive_env_path(old_path)
                or is_sensitive_env_path(new_path)
            ):
                preview_files.extend([old_path, new_path])
        elif not is_sensitive_env_path(file_path):
            preview_files.append(file_path)

    if not preview_files:
        return "No changes to commit."

    preview_parts: list[str] = []
    status = subprocess.run(
        ["git", "status", "--short", "--", *preview_files],
        cwd=prjdir,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        preview_parts.append(status.stdout.strip())

    diff = subprocess.run(
        ["git", "diff", "--no-color", "--", *preview_files],
        cwd=prjdir,
        capture_output=True,
        text=True,
    )
    if diff.stdout.strip():
        preview_parts.append(diff.stdout.strip())

    for file_path in dirty_files:
        if is_sensitive_env_path(file_path):
            continue
        if " -> " in file_path:
            continue
        full_path = os.path.join(prjdir, file_path)
        if not os.path.isfile(full_path):
            continue
        untracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", file_path],
            cwd=prjdir,
            capture_output=True,
            text=True,
        )
        if untracked.returncode == 0:
            continue

        file_diff = subprocess.run(
            ["git", "diff", "--no-color", "--no-index", "--", "/dev/null", file_path],
            cwd=prjdir,
            capture_output=True,
            text=True,
        )
        if file_diff.stdout.strip():
            preview_parts.append(file_diff.stdout.strip())
        else:
            preview_parts.append(f"Untracked file: {file_path}")

    return "\n\n".join(preview_parts) or "No textual diff available."


def generate_commit_message(llm: OpenAICompatibleChatClient, preview: str) -> str:
    system_prompt = (
        "You write concise git commit messages. "
        "Return only the commit message, with no Markdown fences or explanation."
    )
    user_prompt = (
        "Write a clear commit message for these changes.\n\n"
        "Rules:\n"
        "- Use imperative mood.\n"
        "- Keep the first line under 72 characters.\n"
        "- Add a short body only if it materially helps.\n\n"
        f"CHANGES:\n{preview[:12000]}"
    )
    return invoke_text(llm, system_prompt, user_prompt).strip()


def invoke_text(
    llm: OpenAICompatibleChatClient,
    system_prompt: str,
    user_prompt: str,
) -> str:
    started_at = time.monotonic()
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    elapsed = time.monotonic() - started_at
    logging.debug("LLM invoke completed elapsed_seconds=%.3f", elapsed)
    return str(response.content).strip()


def debug_llm_call(
    node_name: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
) -> None:
    debug_user_prompt = re.sub(
        r"(CURRENT FILE STRUCTURE & SYMBOLS(?: [^\n]*)?:\n).*?(?=\n\n(ACTION HISTORY|LAST SCRIPT EXECUTION RESULT|TASK FROM ARCHITECT):)",
        r"\1[FILE TREE OMITTED IN DEBUG LOGS...]\n",
        user_prompt,
        flags=re.DOTALL,
    )
    logging.debug("LLM node=%s system=%s", node_name, system_prompt)
    logging.debug("LLM node=%s user=%s", node_name, debug_user_prompt)
    logging.debug("LLM node=%s response=%s", node_name, response)


def make_thinker(llm: OpenAICompatibleChatClient):
    def thinker(state: AgentState):
        console.print(
            Panel(
                "[bold cyan]Thinker is analyzing the project[/bold cyan]",
                border_style="cyan",
            )
        )
        tree = make_tree(state["prjdir"])
        last_result = ""
        if state["chat_history"]:
            last_result = (
                "LAST SCRIPT EXECUTION RESULT:\n"
                f"{state['chat_history'][-1]}\n\n"
            )
            history_text = format_history(state["chat_history"][:-1])
        else:
            history_text = "No previous actions."
        feedback_text = format_actionable_feedbacks(state)

        system_prompt = (
            "You are the Architect agent of an autonomous coding system. "
            "Analyze the project, the user goal, and previous execution output. "
            "Plan exactly one next step that can be executed by a Python script.\n\n"
            "RULES:\n"
            "1. Do not write code.\n"
            "2. Plan one concrete next step only.\n"
            "3. If file contents are needed, ask for the smallest relevant snippets, symbols, or line ranges; avoid full-file dumps unless the whole file is clearly needed.\n"
            "4. Treat user feedback as active follow-up requirements that may extend or supersede the original goal.\n"
            "5. Generated scripts run from the project root; use project-relative paths in plans, not host absolute project paths.\n"
            "6. If the goal and all actionable user feedback are fully achieved, output only: [DONE]"
        )
        user_prompt = (
            f"PROJECT DIRECTORY HOST PATH: {state['prjdir']}\n"
            "SCRIPT WORKING DIRECTORY: project root. Treat the host path as context only.\n\n"
            f"PROJECT GOAL:\n{state['goal']}\n\n"
            "CURRENT FILE STRUCTURE & SYMBOLS "
            "(fresh snapshot generated immediately before this decision):\n"
            f"{tree}\n\n"
            f"ACTION HISTORY:\n{history_text}\n\n"
            f"USER FEEDBACK:\n{feedback_text}\n\n"
            f"{last_result}"
            "Based on the current state, what is the exact next step?"
        )
        with console.status("[bold green]Consulting LLM...[/bold green]", spinner="dots"):
            plan = invoke_text(llm, system_prompt, user_prompt)
        plan = prevent_premature_done(plan, state.get("pending_feedback", ""))
        plan = force_initial_inspection_for_existing_file_edits(plan, state)
        debug_llm_call("thinker", system_prompt, user_prompt, plan)
        console.print(
            Panel(
                plan,
                title="[bold]Next step[/bold]",
                border_style="blue",
            )
        )
        return {
            "current_plan": plan,
            "iterations": state["iterations"] + 1,
            "implementor_retries": 0,
            "last_error": "",
        }

    return thinker


def make_verify_completion(llm: OpenAICompatibleChatClient):
    def verify_completion(state: AgentState):
        console.print(
            Panel(
                "[bold cyan]Verifying completion with Architect[/bold cyan]",
                border_style="cyan",
            )
        )
        system_prompt = "You are the Architect agent."
        feedback_text = format_actionable_feedbacks(state)
        user_prompt = (
            f"PROJECT GOAL:\n{state['goal']}\n\n"
            f"USER FEEDBACK:\n{feedback_text}\n\n"
            f"ACTION HISTORY:\n{format_history(state['chat_history'])}\n\n"
            "The previous step indicated [DONE]. Are the project goal and all "
            "actionable user feedback successfully applied to the codebase? "
            "User feedback may extend or supersede exact wording in the original "
            "goal. Reply exactly YES or NO."
        )
        with console.status("[bold green]Verifying...[/bold green]", spinner="dots"):
            answer = invoke_text(llm, system_prompt, user_prompt)
        debug_llm_call("verify_completion", system_prompt, user_prompt, answer)
        if "YES" in answer.upper():
            console.print(
                Panel(
                    "[bold green]Goal confirmed as achieved[/bold green]",
                    title="[bold green]Completion check[/bold green]",
                    border_style="green",
                )
            )
            return {
                "current_plan": "[CONFIRMED_DONE]",
                "completion_failures": 0,
            }
        next_failures = state.get("completion_failures", 0) + 1
        console.print(
            Panel(
                (
                    "[bold yellow]Architect requested more work[/bold yellow]\n"
                    f"Completion check attempt {next_failures} of "
                    f"{MAX_COMPLETION_FAILURES}."
                ),
                title="[bold yellow]Completion check[/bold yellow]",
                border_style="yellow",
            )
        )
        return {
            "current_plan": "Completion check failed; continue with the next missing step.",
            "completion_failures": next_failures,
            "chat_history": state["chat_history"]
            + ["Architect tried to finish, but completion was not confirmed."],
        }

    return verify_completion


def make_implementor(llm: OpenAICompatibleChatClient):
    def implementor(state: AgentState):
        console.print(
            Panel(
                (
                    "[bold cyan]Implementor is writing code[/bold cyan] "
                    f"[yellow](attempt {state['implementor_retries'] + 1})[/yellow]"
                ),
                border_style="cyan",
            )
        )
        tree = make_tree(state["prjdir"])
        last_result = ""
        if state["chat_history"]:
            last_result = (
                "LAST SCRIPT EXECUTION RESULT:\n"
                f"{state['chat_history'][-1]}\n\n"
            )
        system_prompt = (
            "You are the Implementor agent. Write one Python script that "
            "executes the Architect task.\n\n"
            "RULES:\n"
            "1. Output only valid Python code wrapped in a ```python fenced block.\n"
            "2. Do not explain the code.\n"
            "3. The script runs from the project root directory. Use relative paths.\n"
            "4. Use standard library file operations when possible.\n"
            "5. If a required file or pattern is missing, raise an exception.\n"
            "6. For multiline file content, prefer Path(...).write_text('\\n'.join([...]) + '\\n', encoding='utf-8'); do not put Markdown code fences inside Python triple-quoted strings.\n"
            "7. Preserve exact validation text from the task; if a command must print `ok`, print exactly `ok`.\n"
            "8. If a validation flag such as --check is required, make that path run before optional third-party imports so validation works in a fresh environment.\n"
            "9. Ignore host absolute project paths in the Architect task; convert them to paths relative to the current working directory.\n"
            "10. If the Architect task asks to inspect, read, print, show, or list snippets, do only that inspection and do not edit files.\n"
            "11. Keep the script compact and robust; prefer direct exact replacements for known text, and avoid broad regex rewrites when a literal replacement is enough."
        )
        user_prompt = (
            f"PROJECT DIRECTORY HOST PATH: {state['prjdir']}\n"
            "SCRIPT WORKING DIRECTORY: project root. Use relative paths from here.\n\n"
            "CURRENT FILE STRUCTURE & SYMBOLS "
            "(fresh snapshot generated immediately before this script request):\n"
            f"{tree}\n\n"
            f"{last_result}"
            f"TASK FROM ARCHITECT:\n{state['current_plan']}\n"
        )
        if state.get("last_error"):
            user_prompt += (
                "\nYour previous code failed with this error:\n"
                f"{state['last_error']}\n"
                "Fix the code and try again."
            )

        with console.status(
            "[bold green]Generating implementation...[/bold green]",
            spinner="dots",
        ):
            try:
                raw_response = invoke_text(llm, system_prompt, user_prompt)
            except LLMTransportError as exc:
                logging.warning("Implementor LLM transport failed: %s", exc)
                error = str(exc).replace("\\", "\\\\").replace('"', '\\"')
                return {
                    "current_code": (
                        'raise RuntimeError("LLM transport failed while generating '
                        f'implementation: {error}")'
                    )
                }
        debug_llm_call("implementor", system_prompt, user_prompt, raw_response)
        return {"current_code": extract_code(raw_response)}

    return implementor


def execute_code(state: AgentState):
    console.print(
        Panel(
            "[bold cyan]Executing generated code[/bold cyan]",
            border_style="cyan",
        )
    )
    result = execute_python_code(
        state["current_code"],
        state["prjdir"],
        executor=state.get("code_executor", "host"),
        docker_image=state.get("code_executor_image", ""),
        docker_network=state.get("code_executor_network", "none"),
        timeout_seconds=state.get(
            "code_executor_timeout_seconds",
            DEFAULT_CODE_EXECUTOR_TIMEOUT_SECONDS,
        ),
        output_limit_bytes=state.get(
            "code_executor_output_limit_bytes",
            DEFAULT_CODE_EXECUTOR_OUTPUT_LIMIT_BYTES,
        ),
        memory=state.get("code_executor_memory", DEFAULT_CODE_EXECUTOR_MEMORY),
        cpus=state.get("code_executor_cpus", DEFAULT_CODE_EXECUTOR_CPUS),
        pids_limit=state.get(
            "code_executor_pids_limit",
            DEFAULT_CODE_EXECUTOR_PIDS_LIMIT,
        ),
    )
    if result.success:
        console.print(
            Panel(
                "[bold green]Execution successful[/bold green]",
                title="[bold green]Execution result[/bold green]",
                border_style="green",
            )
        )
        if result.stdout:
            console.print(
                Panel(
                    result.stdout[:2000],
                    title="[bold]Console output[/bold]",
                    border_style="green",
                )
            )
        diff = get_git_diff(state["prjdir"])
        if diff:
            console.print(
                Panel(
                    Syntax(diff, "diff", theme="monokai", word_wrap=True),
                    title="[bold green]Git diff[/bold green]",
                    border_style="green",
                )
            )
        log_entry = (
            f"Architect planned: {state['current_plan'][:500]}\n"
            "Result: SUCCESS\n"
            f"STDOUT:\n{compact_text(result.stdout, SCRIPT_OUTPUT_HISTORY_LIMIT)}"
        )
        return {
            "chat_history": state["chat_history"] + [compact_history_entry(log_entry)],
            "last_error": "",
            "implementor_retries": 0,
            "pending_feedback": "",
        }

    next_retries = state["implementor_retries"] + 1
    error_report = (
        f"Execution failed with exit code {result.returncode}.\n"
        f"STDOUT:\n{compact_text(result.stdout, SCRIPT_OUTPUT_HISTORY_LIMIT)}\n"
        f"STDERR:\n{compact_text(result.stderr, SCRIPT_OUTPUT_HISTORY_LIMIT)}"
    )
    console.print(
        Panel(
            error_report[:3000],
            title="[bold red]Execution failed[/bold red]",
            border_style="red",
        )
    )
    update = {
        "last_error": error_report,
        "implementor_retries": next_retries,
    }
    if next_retries >= 3:
        update["chat_history"] = state["chat_history"] + [
            compact_history_entry(
                f"Architect planned: {state['current_plan'][:500]}\n"
                f"Result: FAILURE after {next_retries} implementor attempts\n"
                f"{error_report}"
            )
        ]
    return update


def route_after_thinker(state: AgentState):
    plan = state["current_plan"].strip()
    if has_done_marker(plan):
        return "verify_completion"
    if state["iterations"] >= state["max_steps"]:
        console.print("[bold red]Max iterations reached. Stopping.[/bold red]")
        return END
    return "implementor"


def make_ask_user():
    def ask_user(state: AgentState):
        from ui import ask

        console.print(
            Panel(
                (
                    "[bold]Now you can give feedback to the agent.[/bold]\n"
                    "Write [cyan]/commit[/cyan] to review and commit current changes.\n"
                    "Leave empty or write [cyan]/exit[/cyan], [cyan]/quit[/cyan], "
                    "or [cyan]/q[/cyan] to stop."
                ),
                title="[bold yellow]User feedback[/bold yellow]",
                border_style="yellow",
            )
        )
        user_feedback = ask()
        pending_feedback = (
            user_feedback.strip()
            if not is_control_feedback(user_feedback)
            else state.get("pending_feedback", "")
        )
        return {
            "human_feedbacks": state["human_feedbacks"] + [user_feedback],
            "current_plan": "",
            "completion_failures": 0,
            "pending_feedback": pending_feedback,
        }

    return ask_user


def make_route_after_answer(
    commits_enabled: bool,
    llm: OpenAICompatibleChatClient | None = None,
):
    def route_after_answer(state: AgentState):
        last = state["human_feedbacks"][-1].strip()
        if last in {"", "/exit", "/quit", "/q"}:
            return END
        if last == "/commit":
            if not commits_enabled:
                console.print(
                    Panel(
                        "Start the CLI with [bold]--enable-commits[/bold] to use /commit.",
                        border_style="yellow",
                    )
                )
                return "ask_user"

            from dev_env import git

            dirty_files = git.get_dirty_files()
            if not dirty_files:
                console.print("[dim]No changes to commit.[/dim]")
                return "ask_user"

            preview = get_commit_preview(state["prjdir"], dirty_files)
            console.print(
                Panel(
                    Syntax(preview, "diff", theme="monokai", word_wrap=True),
                    title="[bold yellow]Commit preview[/bold yellow]",
                    border_style="yellow",
                )
            )
            mode = Prompt.ask(
                (
                    "[bold yellow]Commit message[/bold yellow] "
                    "[dim](1 = write manually, 2 = ask AI, /cancel = cancel)[/dim]"
                ),
                console=console,
                choices=["1", "2", "/cancel"],
                default="1",
            ).strip()
            if mode == "/cancel":
                console.print("[bold yellow]Commit cancelled.[/bold yellow]")
                return "ask_user"
            if mode == "2":
                if llm is None:
                    console.print("[bold yellow]AI commit message is unavailable.[/bold yellow]")
                    return "ask_user"
                with console.status(
                    "[bold green]Generating commit message...[/bold green]",
                    spinner="dots",
                ):
                    message = generate_commit_message(llm, preview)
                console.print(
                    Panel(
                        message,
                        title="[bold blue]AI commit message[/bold blue]",
                        border_style="blue",
                    )
                )
            else:
                from ui import ask

                message = ask("Commit message")
            if not message:
                console.print("[bold yellow]Commit cancelled.[/bold yellow]")
                return "ask_user"

            git.commit(dirty_files, message)
            console.print(
                Panel(
                    message,
                    title="[bold green]Committed changes[/bold green]",
                    border_style="green",
                )
            )
            return "ask_user"
        return "thinker"

    return route_after_answer


def route_after_answer(state: AgentState):
    last = state["human_feedbacks"][-1]
    if last in {"", "/exit", "/quit", "/q"}:
        return END
    return "thinker"


def make_route_after_verification(interactive: bool):
    def route_after_verification(state: AgentState):
        if state["current_plan"] == "[CONFIRMED_DONE]":
            return "ask_user" if interactive else END
        if state.get("completion_failures", 0) >= MAX_COMPLETION_FAILURES:
            console.print(
                Panel(
                    (
                        "Completion could not be confirmed automatically. "
                        "Returning to feedback instead of looping."
                        if interactive
                        else "Completion could not be confirmed automatically. Stopping."
                    ),
                    title="[bold yellow]Completion check[/bold yellow]",
                    border_style="yellow",
                )
            )
            return "ask_user" if interactive else END
        return "thinker"

    return route_after_verification


def route_after_execution(state: AgentState):
    if state.get("last_error"):
        if state["implementor_retries"] < 3:
            return "implementor"
        return "thinker"
    return "thinker"


def get_initial_state(
    goal: str,
    spec: str = "",
    prjdir: str = ".",
    max_steps: int = 30,
    patience: int = 5,
    action_memory_size: int = 5,
    code_execution: CodeExecutionConfig | None = None,
):
    del patience, action_memory_size
    if code_execution is None:
        code_execution = CodeExecutionConfig()
    full_goal = goal
    if spec:
        full_goal = (
            "PROJECT SPECIFICATION:\n"
            f"{spec}\n\n"
            "CURRENT TASK:\n"
            f"{goal}"
        )
    return AgentState(
        {
            "goal": full_goal,
            "prjdir": prjdir,
            "code_executor": code_execution.executor,
            "code_executor_image": code_execution.docker_image,
            "code_executor_network": code_execution.docker_network,
            "code_executor_timeout_seconds": code_execution.timeout_seconds,
            "code_executor_output_limit_bytes": code_execution.output_limit_bytes,
            "code_executor_memory": code_execution.memory,
            "code_executor_cpus": code_execution.cpus,
            "code_executor_pids_limit": code_execution.pids_limit,
            "chat_history": [],
            "human_feedbacks": [],
            "current_plan": "",
            "current_code": "",
            "last_error": "",
            "implementor_retries": 0,
            "iterations": 0,
            "max_steps": max_steps,
            "completion_failures": 0,
            "pending_feedback": "",
        }
    )


def create_agent(
    commits_enabled: bool = False,
    interactive: bool = False,
    llm_config: LLMConfig | None = None,
):
    llm = create_llm(llm_config)
    graph = StateGraph(state_schema=AgentState)
    graph.add_node("thinker", make_thinker(llm))
    graph.add_node("implementor", make_implementor(llm))
    graph.add_node("execute_code", execute_code)
    graph.add_node("verify_completion", make_verify_completion(llm))
    if interactive:
        graph.add_node("ask_user", make_ask_user())

    graph.set_entry_point("thinker")
    graph.add_conditional_edges("thinker", route_after_thinker)
    graph.add_edge("implementor", "execute_code")
    graph.add_conditional_edges("execute_code", route_after_execution)
    graph.add_conditional_edges(
        "verify_completion",
        make_route_after_verification(interactive),
    )
    if interactive:
        graph.add_conditional_edges("ask_user", make_route_after_answer(commits_enabled, llm))
    return graph.compile()


def run_agent(goal, spec, prjdir=".", max_steps=30):
    initial_state = get_initial_state(
        goal=goal,
        spec=spec,
        prjdir=prjdir,
        max_steps=max_steps,
    )
    create_agent(False).invoke(initial_state)
