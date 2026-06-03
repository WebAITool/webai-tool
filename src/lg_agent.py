import os
import ast
import re
import logging
import warnings
import dotenv
import subprocess
from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from ui import ask

warnings.filterwarnings("ignore", category=FutureWarning, module="smolagents")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

dotenv.load_dotenv()

llm = ChatOpenAI(
    model_name="deepseek/deepseek-v4-flash",
    base_url="https://api.polza.ai/api/v1",
    temperature=0.3,
    api_key=os.getenv('API_KEY')
)

console = Console()


class AgentState(TypedDict):
    goal: str
    prjdir: str
    chat_history: List[str]
    current_plan: str
    current_code: str
    last_error: str
    implementor_retries: int
    iterations: int
    max_steps: int
    human_feedbacks: list[str]


IGNORE_DIRS = {
    '.git',
    '__pycache__',
    'node_modules',
    'venv',
    'env',
    '.venv',
    'dist',
    'build',
    '.pytest_cache'}
IGNORE_EXTS = {
    '.pyc',
    '.pyo',
    '.pyd',
    '.so',
    '.dll',
    '.exe',
    '.jpg',
    '.png',
    '.gif',
    '.pdf',
    '.db',
    '.sqlite3'}


def extract_symbols(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    symbols = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if ext == '.py':
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append(f"class {node.name}")
                elif isinstance(node, ast.FunctionDef):
                    symbols.append(f"def {node.name}")
        elif ext in {'.js', '.ts', '.vue'}:
            class_matches = re.findall(
                r'^[\s]*class\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
            func_matches = re.findall(
                r'^[\s]*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)',
                content,
                re.MULTILINE)
            const_func_matches = re.findall(
                r'^[\s]*(?:export\s+)?const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>',
                content,
                re.MULTILINE)

            for m in class_matches:
                symbols.append(f"class {m}")
            for m in func_matches:
                symbols.append(f"func {m}")
            for m in const_func_matches:
                symbols.append(f"func {m}")
    except Exception:
        pass

    return symbols


def make_tree(prjpath):
    tree_str = ""
    for root, dirs, files in os.walk(prjpath):
        dirs[:] = [
            d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        level = root.replace(prjpath, '').count(os.sep)
        indent = ' ' * 4 * level
        basename = os.path.basename(root)

        if basename:
            tree_str += f"{indent}{basename}/\n"

        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f.startswith('.') or os.path.splitext(f)[
                    1].lower() in IGNORE_EXTS:
                continue

            tree_str += f"{subindent}{f}\n"
            symbols = extract_symbols(os.path.join(root, f))
            for sym in symbols:
                tree_str += f"{subindent}  - {sym}\n"

    return tree_str.strip()


def extract_code(text: str) -> str:
    if "```" in text:
        blocks = text.split("```")
        for block in blocks[1:]:
            if block.strip().startswith("python") or block.strip().startswith("py"):
                first_newline = block.find('\n')
                if first_newline != -1:
                    return block[first_newline:].strip()
                return block.replace("python", "", 1).replace(
                    "py", "", 1).strip()
    return text.strip()


def format_history(history: List[str]) -> str:
    if not history:
        return "No actions taken yet."
    return "\n".join(history)


def get_git_diff(prjdir: str) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--no-color"],
            cwd=prjdir,
            capture_output=True,
            text=True
        )
        diff = result.stdout.strip()
        if diff:
            return diff

        result = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=prjdir,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception:
        return ""


def commit_changes(prjdir: str, message: str = "Agent auto-commit") -> str:
    try:
        subprocess.run(["git", "add", "."], cwd=prjdir,
                       capture_output=True, text=True)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=prjdir,
            capture_output=True,
            text=True
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output
    except Exception as e:
        return f"Commit failed: {e}"


def debug_llm_call(node_name: str, sys_prompt: str,
                   user_prompt: str, response: str):
    def safe_print(text: str):
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('cp1251', errors='replace').decode('cp1251', errors='replace'))

    safe_print(f"\n{'=' * 20} DEBUG: {node_name.upper()} {'=' * 20}")
    safe_print(f"--- SYSTEM PROMPT ---\n{sys_prompt}")

    # Скрываем гигантское дерево файлов только для вывода в консоль
    debug_user_prompt = re.sub(
        r"(CURRENT FILE STRUCTURE & SYMBOLS:\n).*?(?=\n\n(ACTION HISTORY|LAST SCRIPT EXECUTION RESULT|TASK FROM ARCHITECT):)",
        r"\1[FILE TREE OMITTED IN DEBUG LOGS...]\n",
        user_prompt,
        flags=re.DOTALL
    )

    safe_print(f"--- USER PROMPT ---\n{debug_user_prompt}")
    safe_print(f"--- RAW RESPONSE ---\n{response}")
    safe_print(f"{'=' * 60}\n")


def thinker(state: AgentState):
    console.print(Panel(
        "[bold cyan] Thinker is analyzing the project...[/bold cyan]",
        border_style="cyan"
    ))
    if state['chat_history']:
        console.print("[bold]Recent history:[/bold]")
        for entry in state['chat_history'][-3:]:
            console.print(f"  [dim]{entry[:200]}[/dim]")

    tree = make_tree(state['prjdir'])

    sys_prompt = (
        "You are the Architect agent of an autonomous coding system. "
        "Your job is to analyze the current state of the project, read the user's goal, "
        "and plan the SINGLE next logical step for the Implementor agent to execute.\n\n"
        "RULES:\n"
        "1. DO NOT write code. Write a clear, detailed instruction in plain English.\n"
        "2. Only plan ONE step ahead that can be executed via a Python script.\n"
        "3. DO NOT combine a plan with the completion signal. If actions are needed, write the plan.\n"
        "4. CAREFULLY read the Console output of previous actions.\n"
        "5. YOU ARE BLIND to file contents by default. You can instruct the Implementor to write a script that reads and prints the exact contents of that file to the console, so you can see it and decide what to do next.\n"
        "6. If you are absolutely sure the user's goal is FULLY ACHIEVED and NO MORE ACTIONS are needed, output ONLY the exact string: [DONE]"
    )

    last_result = ""
    if state['chat_history']:
        last_result = f"LAST SCRIPT EXECUTION RESULT:\n{state['chat_history'][-1]}\n\n"
        history_text = format_history(state['chat_history'][:-1])
    else:
        history_text = "No previous actions."

    user_prompt = (
        f"PROJECT DIRECTORY: {state['prjdir']}\n\n"
        f"PROJECT GOAL:\n{state['goal']}\n\n"
        f"CURRENT FILE STRUCTURE & SYMBOLS:\n{tree}\n\n"
        f"ACTION HISTORY:\n{history_text}\n\n"
        f"LIST OF FEEDBACKS FROM USER:\n{
            '\n'.join(
                state['human_feedbacks'])}\nEND OF LIST"
        f"{last_result}"
        "Based on the history, last execution result, and current structure, what is the exact next step? "
        "If the goal is fully completed, reply with [DONE]."
    )

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=user_prompt)
    ]

    with console.status("[bold green] Consulting LLM...", spinner="dots"):
        response = llm.invoke(messages)
    plan = response.content.strip()

    debug_llm_call("Thinker", sys_prompt, user_prompt, plan)

    return {
        "current_plan": plan,
        "iterations": state["iterations"] + 1,
        "implementor_retries": 0,
        "last_error": ""
    }


def verify_completion(state: AgentState):
    console.print(Panel(
        "[bold cyan] Verifying completion with Architect...[/bold cyan]",
        border_style="cyan"
    ))

    sys_prompt = "You are the Architect agent."
    user_prompt = (
        f"PROJECT GOAL:\n{state['goal']}\n\n"
        f"ACTION HISTORY:\n{format_history(state['chat_history'])}\n\n"
        "You indicated that the goal is [DONE]. "
        "Review the action history. Have the required changes been successfully applied to the codebase? "
        "Reply EXACTLY with 'YES' to confirm completion and stop the agent, or 'NO' if a critical step was missed."
    )

    messages = [
        SystemMessage(
            content=sys_prompt), HumanMessage(
            content=user_prompt)]
    with console.status("[bold green] Verifying...", spinner="dots"):
        response = llm.invoke(messages)
    answer = response.content.strip()

    debug_llm_call("Verify Completion", sys_prompt, user_prompt, answer)

    answer_upper = answer.upper()
    if "YES" in answer_upper:
        diff = get_git_diff(state['prjdir'])
        if diff:
            console.print(Panel(
                Syntax(diff, "diff", theme="monokai"),
                title="[bold green]Final Git Diff[/bold green]",
                border_style="green"
            ))
        else:
            console.print("[bold green] Goal confirmed as achieved![/bold green]")
        return {"current_plan": "[CONFIRMED_DONE]"}
    else:
        console.print("[bold yellow] Architect thinks more work is needed[/bold yellow]")
        return {
            "current_plan": "Previous completion check failed. Architect realized more work is needed.",
            "chat_history": state["chat_history"] + ["Architect tried to finish, but realized the goal is not fully achieved yet."]
        }


def implementor(state: AgentState):
    console.print(Panel(
        f"[bold cyan] Implementor is writing code[/bold cyan] [yellow](Attempt {state['implementor_retries'] + 1})[/yellow]",
        border_style="cyan"
    ))

    tree = make_tree(state['prjdir'])

    sys_prompt = (
        "You are the Implementor agent. Your job is to write a Python script "
        "that executes the task requested by the Architect.\n\n"
        "RULES:\n"
        "1. Output ONLY valid Python code wrapped in ```python ... ``` block.\n"
        "2. Do not explain the code. Just write it.\n"
        "3. The script will be executed directly in the project root directory. Use RELATIVE paths.\n"
        "4. Use standard libraries (os, shutil, re, etc.) to read, create, or modify files.\n"
        "5. NEVER fail silently. If you cannot find a file, a class, or a specific string pattern to modify, "
        "you MUST raise an exception (e.g., raise ValueError('Could not find class X')) or use sys.exit(1). "
        "Do not just print an error and return."
    )

    last_result = ""
    if state['chat_history']:
        last_result = f"LAST SCRIPT EXECUTION RESULT:\n{state['chat_history'][-1]}\n\n"

    user_prompt = (
        f"CURRENT FILE STRUCTURE & SYMBOLS:\n{tree}\n\n"
        f"{last_result}"
        f"TASK FROM ARCHITECT:\n{state['current_plan']}\n"
    )

    if state.get("last_error"):
        user_prompt += (
            "\nWARNING! Your previous code attempt failed with this error:\n"
            f"{state['last_error']}\n"
            "Read the traceback carefully, fix the code, and try again."
        )

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=user_prompt)
    ]

    with console.status("[bold green] Generating implementation...", spinner="dots"):
        response = llm.invoke(messages)
    code = extract_code(response.content)

    return {"current_code": code}


def execute_code(state: AgentState):
    console.print(Panel(
        "[bold cyan] Executing generated code...[/bold cyan]",
        border_style="cyan"
    ))
    code = state['current_code']
    prjdir = state['prjdir']

    temp_script_path = os.path.join(prjdir, '.agent_script.py')

    try:
        with console.status("[bold green] Running code...[/bold green]", spinner="dots"):
            with open(temp_script_path, 'w', encoding='utf-8') as f:
                f.write(code)

            result = subprocess.run(
                ["python", ".agent_script.py"],
                cwd=prjdir,
                capture_output=True,
                text=True
            )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode == 0:
            console.print("[bold green] Execution successful[/bold green]")
            if stdout:
                console.print(Panel(
                    stdout[:2000],
                    title="[bold]Console Output[/bold]",
                    border_style="green"
                ))
            diff = get_git_diff(prjdir)
            if diff:
                console.print(Panel(
                    Syntax(diff, "diff", theme="monokai"),
                    title="[bold yellow]Changes Applied[/bold yellow]",
                    border_style="yellow"
                ))
            else:
                console.print(Panel(
                    "[dim]No file changes detected[/dim]",
                    title="[bold yellow]Changes Applied[/bold yellow]",
                    border_style="yellow"
                ))
            log_entry = f"Architect planned: '{state['current_plan'][:100]}...'\nResult: SUCCESS.\nConsole: {stdout[:10000]}"
            return {
                "chat_history": state["chat_history"] + [log_entry],
                "last_error": "",
                "implementor_retries": 0
            }
        else:
            error_report = "Execution failed with non-zero exit code.\n"
            if stdout:
                error_report += f"\n--- STDOUT ---\n{stdout[:10000]}\n"
            if stderr:
                error_report += f"\n--- STDERR (Traceback) ---\n{stderr[:10000]}\n"

            console.print(Panel(
                f"[bold red] Execution failed[/bold red]\n\n{error_report[:2000]}",
                border_style="red"
            ))
            return {
                "last_error": error_report,
                "implementor_retries": state["implementor_retries"] + 1
            }
    finally:
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)


def route_after_thinker(state: AgentState):
    plan = state["current_plan"]

    if "[DONE]" in plan:
        clean_plan = plan.replace("[DONE]", "").strip()
        if len(clean_plan) > 50:
            console.print("[bold yellow] Thinker included [DONE] inside larger plan. Routing to Implementor.[/bold yellow]")
            return "implementor"
        else:
            return "verify_completion"

    if state["iterations"] >= state["max_steps"]:
        console.print("[bold red] Max iterations reached. Stopping.[/bold red]")
        return END

    return "implementor"


def ask_user(state: AgentState):
    console.print(Panel(
        "[bold]Available commands:[/bold]\n"
        "  [cyan]/commit[/cyan]   — Commit all changes to git\n"
        "  [cyan]/exit[/cyan]     — Exit (or empty answer)\n"
        "  [cyan]any text[/cyan]  — Send feedback to agent",
        title="[bold yellow]User Feedback[/bold yellow]",
        border_style="yellow"
    ))
    user_feedback = ask()

    return {
        'human_feedbacks': state['human_feedbacks'] + [user_feedback]
    }


def route_after_answer(state: AgentState):
    last = state['human_feedbacks'][-1]
    if len(last) == 0 or last == '/exit' or last == '/quit' or last == '/q':
        return END

    if last == '/commit':
        console.print("[bold cyan]Committing changes...[/bold cyan]")
        result = commit_changes(state['prjdir'])
        console.print(Panel(
            result,
            title="[bold]Commit Result[/bold]",
            border_style="green"
        ))
        return 'ask_user'

    return 'thinker'


def route_after_verification(state: AgentState):
    if "[CONFIRMED_DONE]" in state["current_plan"]:
        console.print("[bold green] Goal confirmed as achieved! Showing changes...[/bold green]")
        return "ask_user"
    else:
        console.print("[bold yellow] Architect decided to continue working...[/bold yellow]")
        return "thinker"


def route_after_execution(state: AgentState):
    if state.get("last_error"):
        if state["implementor_retries"] < 1:
            console.print("[bold yellow] Implementor retrying to fix error...[/bold yellow]")
            return "implementor"
        else:
            console.print("[bold red] Implementor failed. Returning to Thinker for new plan...[/bold red]")
            fail_log = f"Architect planned: '{state['current_plan'][:100]}...'\nResult: FAILED completely after 3 attempts. Last error: {state['last_error'][:300]}"
            state["chat_history"].append(fail_log)
            return "thinker"

    return "thinker"


def get_initial_state(goal: str, prjdir: str,
                      max_steps: int = 30) -> AgentState:
    return {
        "goal": goal,
        "prjdir": prjdir,
        "chat_history": [],
        "current_plan": "",
        "current_code": "",
        "last_error": "",
        "implementor_retries": 0,
        "iterations": 0,
        "max_steps": max_steps,
        "human_feedbacks": []
    }


def create_agent():
    graph = StateGraph(state_schema=AgentState)

    graph.add_node("thinker", thinker)
    graph.add_node("implementor", implementor)
    graph.add_node("execute_code", execute_code)
    graph.add_node("verify_completion", verify_completion)
    graph.add_node("ask_user", ask_user)

    graph.set_entry_point("thinker")

    graph.add_conditional_edges("thinker", route_after_thinker)
    graph.add_conditional_edges("verify_completion", route_after_verification)
    graph.add_edge("implementor", "execute_code")
    graph.add_conditional_edges("execute_code", route_after_execution)
    graph.add_conditional_edges("ask_user", route_after_answer)

    return graph.compile()