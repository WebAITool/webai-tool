import ast
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from typing import List, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from llm_config import LLMConfig, load_llm_config


IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    "env",
    ".venv",
    "dist",
    "build",
    ".pytest_cache",
}
IGNORE_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".exe",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".pdf",
    ".db",
    ".sqlite3",
}


@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str


class AgentState(TypedDict):
    goal: str
    prjdir: str
    chat_history: List[str]
    human_feedbacks: List[str]
    current_plan: str
    current_code: str
    last_error: str
    implementor_retries: int
    iterations: int
    max_steps: int


def create_llm(config: LLMConfig | None = None) -> ChatOpenAI:
    if config is None:
        config = load_llm_config()
    return ChatOpenAI(
        model_name=config.model,
        base_url=config.api_base_url,
        temperature=0.3,
        api_key=config.api_key,
    )


def extract_symbols(filepath: str) -> list[str]:
    ext = os.path.splitext(filepath)[1].lower()
    symbols: list[str] = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if ext == ".py":
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append(f"class {node.name}")
                elif isinstance(node, ast.FunctionDef):
                    symbols.append(f"def {node.name}")
        elif ext in {".js", ".ts", ".vue"}:
            class_matches = re.findall(
                r"^[\s]*class\s+([a-zA-Z0-9_]+)",
                content,
                re.MULTILINE,
            )
            func_matches = re.findall(
                r"^[\s]*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)",
                content,
                re.MULTILINE,
            )
            const_func_matches = re.findall(
                r"^[\s]*(?:export\s+)?const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>",
                content,
                re.MULTILINE,
            )
            symbols.extend(f"class {match}" for match in class_matches)
            symbols.extend(f"func {match}" for match in func_matches)
            symbols.extend(f"func {match}" for match in const_func_matches)
    except Exception:
        pass
    return symbols


def make_tree(prjpath: str) -> str:
    tree = ""
    for root, dirs, files in os.walk(prjpath):
        dirs[:] = [
            d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")
        ]
        level = root.replace(prjpath, "").count(os.sep)
        indent = " " * 4 * level
        basename = os.path.basename(root)

        if basename:
            tree += f"{indent}{basename}/\n"

        subindent = " " * 4 * (level + 1)
        for file_name in files:
            ext = os.path.splitext(file_name)[1].lower()
            if file_name.startswith(".") or ext in IGNORE_EXTS:
                continue
            filepath = os.path.join(root, file_name)
            tree += f"{subindent}{file_name}\n"
            for symbol in extract_symbols(filepath):
                tree += f"{subindent}  - {symbol}\n"

    return tree.strip() or "(empty project)"


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


def execute_python_code(code: str, prjdir: str) -> ExecutionResult:
    temp_script_path = os.path.join(prjdir, ".agent_script.py")
    try:
        with open(temp_script_path, "w", encoding="utf-8") as file:
            file.write(code)

        result = subprocess.run(
            ["python", ".agent_script.py"],
            cwd=prjdir,
            capture_output=True,
            text=True,
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


def format_history(history: List[str]) -> str:
    if not history:
        return "No actions taken yet."
    return "\n".join(history)


def invoke_text(llm: ChatOpenAI, system_prompt: str, user_prompt: str) -> str:
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    return str(response.content).strip()


def debug_llm_call(
    node_name: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
) -> None:
    debug_user_prompt = re.sub(
        r"(CURRENT FILE STRUCTURE & SYMBOLS:\n).*?(?=\n\n(ACTION HISTORY|LAST SCRIPT EXECUTION RESULT|TASK FROM ARCHITECT):)",
        r"\1[FILE TREE OMITTED IN DEBUG LOGS...]\n",
        user_prompt,
        flags=re.DOTALL,
    )
    logging.debug("LLM node=%s system=%s", node_name, system_prompt)
    logging.debug("LLM node=%s user=%s", node_name, debug_user_prompt)
    logging.debug("LLM node=%s response=%s", node_name, response)


def make_thinker(llm: ChatOpenAI):
    def thinker(state: AgentState):
        print("thinking...")
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
        feedback_text = "\n".join(state.get("human_feedbacks", []))
        if not feedback_text:
            feedback_text = "No user feedback."

        system_prompt = (
            "You are the Architect agent of an autonomous coding system. "
            "Analyze the project, the user goal, and previous execution output. "
            "Plan exactly one next step that can be executed by a Python script.\n\n"
            "RULES:\n"
            "1. Do not write code.\n"
            "2. Plan one concrete next step only.\n"
            "3. If file contents are needed, ask the Implementor to read and print them.\n"
            "4. If the goal is fully achieved, output only: [DONE]"
        )
        user_prompt = (
            f"PROJECT DIRECTORY: {state['prjdir']}\n\n"
            f"PROJECT GOAL:\n{state['goal']}\n\n"
            f"CURRENT FILE STRUCTURE & SYMBOLS:\n{tree}\n\n"
            f"ACTION HISTORY:\n{history_text}\n\n"
            f"USER FEEDBACK:\n{feedback_text}\n\n"
            f"{last_result}"
            "Based on the current state, what is the exact next step?"
        )
        plan = invoke_text(llm, system_prompt, user_prompt)
        debug_llm_call("thinker", system_prompt, user_prompt, plan)
        print(plan)
        return {
            "current_plan": plan,
            "iterations": state["iterations"] + 1,
            "implementor_retries": 0,
            "last_error": "",
        }

    return thinker


def make_verify_completion(llm: ChatOpenAI):
    def verify_completion(state: AgentState):
        print("trying to end...")
        system_prompt = "You are the Architect agent."
        user_prompt = (
            f"PROJECT GOAL:\n{state['goal']}\n\n"
            f"ACTION HISTORY:\n{format_history(state['chat_history'])}\n\n"
            "The previous step indicated [DONE]. Are the required changes "
            "successfully applied to the codebase? Reply exactly YES or NO."
        )
        answer = invoke_text(llm, system_prompt, user_prompt)
        debug_llm_call("verify_completion", system_prompt, user_prompt, answer)
        if "YES" in answer.upper():
            return {"current_plan": "[CONFIRMED_DONE]"}
        return {
            "current_plan": "Completion check failed; continue with the next missing step.",
            "chat_history": state["chat_history"]
            + ["Architect tried to finish, but completion was not confirmed."],
        }

    return verify_completion


def make_implementor(llm: ChatOpenAI):
    def implementor(state: AgentState):
        print(f"code writing... attempt {state['implementor_retries'] + 1}")
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
            "8. If a validation flag such as --check is required, make that path run before optional third-party imports so validation works in a fresh environment."
        )
        user_prompt = (
            f"CURRENT FILE STRUCTURE & SYMBOLS:\n{tree}\n\n"
            f"{last_result}"
            f"TASK FROM ARCHITECT:\n{state['current_plan']}\n"
        )
        if state.get("last_error"):
            user_prompt += (
                "\nYour previous code failed with this error:\n"
                f"{state['last_error']}\n"
                "Fix the code and try again."
            )

        raw_response = invoke_text(llm, system_prompt, user_prompt)
        debug_llm_call("implementor", system_prompt, user_prompt, raw_response)
        return {"current_code": extract_code(raw_response)}

    return implementor


def execute_code(state: AgentState):
    print("code executing...")
    result = execute_python_code(state["current_code"], state["prjdir"])
    if result.success:
        log_entry = (
            f"Architect planned: {state['current_plan'][:500]}\n"
            "Result: SUCCESS\n"
            f"STDOUT:\n{result.stdout[:10000]}"
        )
        return {
            "chat_history": state["chat_history"] + [log_entry],
            "last_error": "",
            "implementor_retries": 0,
        }

    next_retries = state["implementor_retries"] + 1
    error_report = (
        f"Execution failed with exit code {result.returncode}.\n"
        f"STDOUT:\n{result.stdout[:10000]}\n"
        f"STDERR:\n{result.stderr[:10000]}"
    )
    print("ERROR:", error_report)
    update = {
        "last_error": error_report,
        "implementor_retries": next_retries,
    }
    if next_retries >= 3:
        update["chat_history"] = state["chat_history"] + [
            f"Architect planned: {state['current_plan'][:500]}\n"
            f"Result: FAILURE after {next_retries} implementor attempts\n"
            f"{error_report}"
        ]
    return update


def route_after_thinker(state: AgentState):
    plan = state["current_plan"].strip()
    if "[DONE]" in plan.upper():
        return "verify_completion"
    if state["iterations"] >= state["max_steps"]:
        print("Max iterations reached. Stopping.")
        return END
    return "implementor"


def make_ask_user():
    def ask_user(state: AgentState):
        from ui import ask

        print(
            "Now you can give feedback to agent.\n"
            "If you want to leave, give an empty answer or write /exit, /quit or /q"
        )
        user_feedback = ask()
        return {
            "human_feedbacks": state["human_feedbacks"] + [user_feedback],
        }

    return ask_user


def route_after_answer(state: AgentState):
    last = state["human_feedbacks"][-1]
    if last in {"", "/exit", "/quit", "/q"}:
        return END
    return "thinker"


def make_route_after_verification(interactive: bool):
    def route_after_verification(state: AgentState):
        if state["current_plan"] == "[CONFIRMED_DONE]":
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
):
    del patience, action_memory_size
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
            "chat_history": [],
            "human_feedbacks": [],
            "current_plan": "",
            "current_code": "",
            "last_error": "",
            "implementor_retries": 0,
            "iterations": 0,
            "max_steps": max_steps,
        }
    )


def create_agent(
    commits_enabled: bool = False,
    interactive: bool = False,
    llm_config: LLMConfig | None = None,
):
    del commits_enabled
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
        graph.add_conditional_edges("ask_user", route_after_answer)
    return graph.compile()


def run_agent(goal, spec, prjdir=".", max_steps=30):
    initial_state = get_initial_state(
        goal=goal,
        spec=spec,
        prjdir=prjdir,
        max_steps=max_steps,
    )
    create_agent(False).invoke(initial_state)
