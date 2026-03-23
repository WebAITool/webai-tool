from graph.models import ImportTag
from graph.repo_graph import RepoGraphLite
from repo_map import Tag


def _make_graph(tags, imports=None, bindings=None, receivers=None):
    g = RepoGraphLite()
    g.build_from(tags, imports or [], bindings or [], receivers or [])
    return g


def test_impact_upstream_depth1():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="handle", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="login", line=5, kind="ref",
            scope="handle", capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="views.py", imported_name="login",
                  source_path="auth", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    result = g.impact("login", direction="upstream", max_depth=1)
    assert "handle" in result
    assert "WILL BREAK" in result


def test_impact_downstream():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="auth.py", name="validate", line=10, kind="def",
            capture_name="name.definition.function"),
        Tag(file="auth.py", name="validate", line=3, kind="ref",
            scope="login", capture_name="name.reference.call"),
    ]
    g = _make_graph(tags)
    result = g.impact("login", direction="downstream", max_depth=1)
    assert "validate" in result


def test_impact_min_confidence_filter():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="handle", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="login", line=5, kind="ref",
            scope="handle", capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="views.py", imported_name="login",
                  source_path="auth", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    result = g.impact("login", direction="upstream", min_confidence=0.96)
    assert "WILL BREAK" not in result
    result2 = g.impact("login", direction="upstream", min_confidence=0.9)
    assert "WILL BREAK" in result2


def test_impact_depth_limit():
    tags = [
        Tag(file="a.py", name="func_a", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="b.py", name="func_b", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="b.py", name="func_a", line=5, kind="ref",
            scope="func_b", capture_name="name.reference.call"),
        Tag(file="c.py", name="func_c", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="c.py", name="func_b", line=5, kind="ref",
            scope="func_c", capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="b.py", imported_name="func_a",
                  source_path="a", is_relative=False, line=1),
        ImportTag(file="c.py", imported_name="func_b",
                  source_path="b", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    result = g.impact("func_a", direction="upstream", max_depth=1)
    assert "func_b" in result
    assert "func_c" not in result


def test_impact_cycle_handling():
    tags = [
        Tag(file="a.py", name="func_a", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="b.py", name="func_b", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="a.py", name="func_b", line=5, kind="ref",
            scope="func_a", capture_name="name.reference.call"),
        Tag(file="b.py", name="func_a", line=5, kind="ref",
            scope="func_b", capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="a.py", imported_name="func_b",
                  source_path="b", is_relative=False, line=1),
        ImportTag(file="b.py", imported_name="func_a",
                  source_path="a", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    result = g.impact("func_a", direction="upstream", max_depth=5)
    assert "func_b" in result


def test_impact_risk_rating():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
    ]
    for i in range(3):
        fname = f"view{i}.py"
        tags.extend([
            Tag(file=fname, name=f"handler{i}", line=1, kind="def",
                capture_name="name.definition.function"),
            Tag(file=fname, name="login", line=5, kind="ref",
                scope=f"handler{i}", capture_name="name.reference.call"),
        ])
    imports = [
        ImportTag(file=f"view{i}.py", imported_name="login",
                  source_path="auth", is_relative=False, line=1)
        for i in range(3)
    ]
    g = _make_graph(tags, imports=imports)
    result = g.impact("login", direction="upstream")
    assert "MEDIUM" in result


def test_impact_not_found():
    g = _make_graph([])
    result = g.impact("nonexistent")
    assert "not found" in result.lower()


def test_impact_file_disambiguation():
    tags = [
        Tag(file="auth.py", name="validate", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="orders.py", name="validate", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="handler", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="validate", line=5, kind="ref",
            scope="handler", capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="views.py", imported_name="validate",
                  source_path="auth", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    result = g.impact("validate", file="auth.py", direction="upstream")
    assert "auth.py" in result
