from graph.repo_graph import RepoGraphLite
from repo_map import Tag


def _make_graph(tags, imports=None, bindings=None, receivers=None):
    g = RepoGraphLite()
    g.build_from(tags, imports or [], bindings or [], receivers or [])
    return g


def test_search_exact_name_match():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="auth.py", name="logout", line=10, kind="def",
            capture_name="name.definition.function"),
    ]
    g = _make_graph(tags)
    result = g.search("login")
    assert "login" in result
    assert "score" in result  # BM25 float score


def test_search_substring_match():
    tags = [
        Tag(file="auth.py", name="handle_login", line=1, kind="def",
            capture_name="name.definition.function"),
    ]
    g = _make_graph(tags)
    result = g.search("login")
    assert "handle_login" in result
    assert "score" in result  # BM25 float score


def test_search_case_insensitive():
    tags = [
        Tag(file="auth.py", name="UserService", line=1, kind="def",
            capture_name="name.definition.class"),
    ]
    g = _make_graph(tags)
    result = g.search("userservice")
    assert "UserService" in result


def test_search_kind_filter():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="auth.py", name="login", line=10, kind="def",
            scope="AuthService", capture_name="name.definition.function",
            node_type="function_definition"),
    ]
    g = _make_graph(tags)
    result = g.search("login", kind="Method")
    assert "Method" in result
    assert "Function" not in result.split("Method")[0]


def test_search_limit():
    tags = [
        Tag(file=f"f{i}.py", name=f"func{i}", line=1, kind="def",
            capture_name="name.definition.function")
        for i in range(20)
    ]
    g = _make_graph(tags)
    result = g.search("func", limit=5)
    entries = [line for line in result.split("\n") if "func" in line and "(" in line]
    assert len(entries) <= 5


def test_search_empty():
    g = _make_graph([])
    result = g.search("nonexistent")
    assert "0 found" in result


def test_search_deterministic_ordering():
    tags = [
        Tag(file="b.py", name="validate", line=5, kind="def",
            capture_name="name.definition.function"),
        Tag(file="a.py", name="validate", line=10, kind="def",
            capture_name="name.definition.function"),
    ]
    g = _make_graph(tags)
    result = g.search("validate")
    a_pos = result.index("a.py")
    b_pos = result.index("b.py")
    assert a_pos < b_pos
