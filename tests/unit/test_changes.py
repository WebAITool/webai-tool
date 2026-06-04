import textwrap
from tools.changes import _parse_diff, _map_lines_to_symbols
from graph.models import SymbolNode


def test_parse_diff_basic():
    diff_text = textwrap.dedent("""\
        diff --git a/auth.py b/auth.py
        --- a/auth.py
        +++ b/auth.py
        @@ -10,3 +10,4 @@ def login():
             pass
        +    return True
             # end
    """)
    result = _parse_diff(diff_text)
    assert "auth.py" in result
    assert 11 in result["auth.py"]


def test_parse_diff_empty():
    result = _parse_diff("")
    assert result == {}


def test_parse_diff_multiple_files():
    diff_text = textwrap.dedent("""\
        diff --git a/a.py b/a.py
        --- a/a.py
        +++ b/a.py
        @@ -1,2 +1,3 @@
         line1
        +new_line
         line2
        diff --git a/b.py b/b.py
        --- a/b.py
        +++ b/b.py
        @@ -5,2 +5,3 @@
         old
        +added
         end
    """)
    result = _parse_diff(diff_text)
    assert "a.py" in result
    assert "b.py" in result


def test_map_lines_to_symbols_nearest_preceding():
    symbols = [
        SymbolNode(id="Function:login:auth.py", kind="Function",
                   name="login", file="auth.py", line=5, scope="", is_exported=False),
        SymbolNode(id="Function:logout:auth.py", kind="Function",
                   name="logout", file="auth.py", line=20, scope="", is_exported=False),
    ]
    result = _map_lines_to_symbols({10, 12}, symbols)
    assert len(result) == 1
    assert result[0].name == "login"


def test_map_lines_to_symbols_before_first():
    symbols = [
        SymbolNode(id="Function:login:auth.py", kind="Function",
                   name="login", file="auth.py", line=10, scope="", is_exported=False),
    ]
    result = _map_lines_to_symbols({3}, symbols)
    assert len(result) == 0


def test_map_lines_to_symbols_dedup():
    symbols = [
        SymbolNode(id="Function:login:auth.py", kind="Function",
                   name="login", file="auth.py", line=5, scope="", is_exported=False),
    ]
    result = _map_lines_to_symbols({6, 7, 8}, symbols)
    assert len(result) == 1
