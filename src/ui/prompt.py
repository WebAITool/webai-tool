from rich.console import Console
from rich.panel import Panel
from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout

console = Console()


def _key_bindings() -> KeyBindings:
    bindings = KeyBindings()

    @bindings.add("escape", "enter")
    def _(event):
        event.app.exit(result=event.app.current_buffer.text)

    @bindings.add("c-d")
    def _(event):
        event.app.exit(result=event.app.current_buffer.text)

    return bindings


def ask(prompt: str = "Your feedback") -> str:
    console.print(
        Panel(
            (
                "[bold]Enter[/bold] adds a new line.\n"
                "[bold]Esc+Enter[/bold] or [bold]Ctrl+D[/bold] sends the text.\n"
                "[bold]Ctrl+C[/bold] cancels."
            ),
            title=f"[bold yellow]{prompt}[/bold yellow]",
            border_style="yellow",
        )
    )
    session = PromptSession(
        HTML("<ansiyellow> > </ansiyellow>"),
        multiline=True,
        complete_while_typing=False,
        erase_when_done=False,
        key_bindings=_key_bindings(),
        reserve_space_for_menu=0,
    )
    try:
        with patch_stdout():
            return session.prompt().strip()
    except (KeyboardInterrupt, EOFError):
        return ""
