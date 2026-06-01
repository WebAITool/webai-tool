from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style


STYLE = Style.from_dict({
    "frame.border": "#884444"
})
session = PromptSession()


def ask() -> str:
    return session.prompt(" > ", style=STYLE, show_frame=True)
