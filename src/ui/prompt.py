from rich.console import Console
from rich.prompt import Prompt

console = Console()


def ask() -> str:
    return Prompt.ask(
        "[bold yellow] Your feedback[/bold yellow]",
        console=console,
        default=""
    )