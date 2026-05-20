from prompt_toolkit import prompt
from prompt_toolkit.styles import Style


STYLE = Style.from_dict({
    "frame.border": "#884444"
})


def ask() -> str:
    return prompt(" > ", style=STYLE, show_frame=True)
