from langchain_core.tools import tool
import subprocess
import os
import platform


def _shell_command(cmd: str) -> list[str]:
    if platform.system() == "Windows":
        return ["cmd", "/C", cmd]
    return ["sh", "-lc", cmd]


@tool
def shell_exec(cmd: str) -> str:
    """Executes a shell command and returns its output.
    Supports any commands.

    Args:
        cmd (str): command to be executed

    Returns:
        str: success or error message.
    """

    result = subprocess.run(
        _shell_command(cmd),
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=os.getcwd()
    )
    stdout = result.stdout
    stderr = result.stderr

    if result.returncode == 0:
        output = stdout.strip()
        return output if output else "Command executed successfully."
    else:
        error = stderr.strip() if stderr else ""
        return f"Error (code {result.returncode}):\n{error}"
