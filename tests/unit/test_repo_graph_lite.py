# tests/unit/test_repo_graph_lite.py
from graph.models import ImportTag, TypeBinding, ReceiverTag
from graph.repo_graph import RepoGraphLite
from repo_map import Tag


def _make_graph(tags: list[Tag],
                imports: list[ImportTag] | None = None,
                bindings: list[TypeBinding] | None = None,
                receivers: list[ReceiverTag] | None = None) -> RepoGraphLite:
    g = RepoGraphLite()
    g.build_from(tags, imports or [], bindings or [], receivers or [])
    return g


def test_same_file_edge():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="auth.py", name="login", line=5, kind="ref",
            capture_name="name.reference.call"),
    ]
    g = _make_graph(tags)
    assert any(e.reason == "same-file" and e.confidence == 1.0 for e in g.edges)


def test_import_resolved_edge():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="login", line=5, kind="ref",
            capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="views.py", imported_name="login",
                  source_path="auth", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    edges = [e for e in g.edges if e.reason == "import-resolved"]
    assert len(edges) == 1
    assert edges[0].confidence == 0.95


def test_ambiguous_no_edge():
    tags = [
        Tag(file="auth.py", name="get", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="models.py", name="get", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="get", line=5, kind="ref",
            capture_name="name.reference.call"),
    ]
    g = _make_graph(tags)
    assert not any(e.source_id.endswith("views.py") for e in g.edges
                   if "get" in e.source_id)


def test_global_unique_edge():
    tags = [
        Tag(file="auth.py", name="validate_token", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="validate_token", line=5, kind="ref",
            capture_name="name.reference.call"),
    ]
    g = _make_graph(tags)
    edges = [e for e in g.edges if e.reason == "global-unique"]
    assert len(edges) == 1
    assert edges[0].confidence == 0.7


def test_self_access_edge():
    tags = [
        # The enclosing method "login" belongs to UserService
        Tag(file="auth.py", name="login", line=1, kind="def",
            scope="UserService", capture_name="name.definition.function",
            node_type="function_definition"),
        # The target method "validate" also belongs to UserService
        Tag(file="auth.py", name="validate", line=5, kind="def",
            scope="UserService", capture_name="name.definition.function",
            node_type="function_definition"),
        # The ref to "validate" is called from inside "login" — so scope="login"
        Tag(file="auth.py", name="validate", line=20, kind="ref",
            scope="login", capture_name="name.reference.call"),
    ]
    receivers = [
        # receiver_name="self" at line 20, inside scope="login"
        ReceiverTag(file="auth.py", receiver_name="self",
                    method_name="validate", line=20, scope="login"),
    ]
    g = _make_graph(tags, receivers=receivers)
    self_edges = [e for e in g.edges if e.reason == "self-access"]
    assert len(self_edges) == 1
    assert self_edges[0].confidence == 1.0


def test_type_resolved_edge():
    """Priority 4: obj.method() + TypeBinding for obj resolves to a class."""
    tags = [
        Tag(file="auth.py", name="validate", line=1, kind="def",
            scope="UserService", capture_name="name.definition.function",
            node_type="function_definition"),
        Tag(file="views.py", name="validate", line=10, kind="ref",
            scope="handle", capture_name="name.reference.call"),
    ]
    bindings = [
        TypeBinding(file="views.py", var_name="svc",
                    resolved_type="UserService", scope="handle", source="constructor"),
    ]
    receivers = [
        ReceiverTag(file="views.py", receiver_name="svc",
                    method_name="validate", line=10, scope="handle"),
    ]
    g = _make_graph(tags, bindings=bindings, receivers=receivers)
    type_edges = [e for e in g.edges if e.reason == "type-resolved"]
    assert len(type_edges) == 1
    assert type_edges[0].confidence == 0.9


def test_scope_match_edge():
    """Priority 5: exactly one def of the called name in the same enclosing class as the ref."""
    tags = [
        Tag(file="auth.py", name="validate", line=5, kind="def",
            scope="UserService", capture_name="name.definition.function",
            node_type="function_definition"),
        Tag(file="other.py", name="validate", line=5, kind="def",
            scope="OrderService", capture_name="name.definition.function",
            node_type="function_definition"),
        Tag(file="views.py", name="validate", line=10, kind="ref",
            scope="UserService", capture_name="name.reference.call"),
    ]
    g = _make_graph(tags)
    scope_edges = [e for e in g.edges if e.reason == "scope-match"]
    assert len(scope_edges) == 1
    assert scope_edges[0].confidence == 0.85


def test_unique_method_edge():
    """Priority 7: only one class has a method with this name."""
    tags = [
        Tag(file="auth.py", name="validate", line=1, kind="def",
            scope="UserService", capture_name="name.definition.function",
            node_type="function_definition"),
        Tag(file="other.py", name="validate", line=1, kind="def",
            scope="UserService", capture_name="name.definition.function",
            node_type="function_definition"),
        Tag(file="views.py", name="validate", line=10, kind="ref",
            capture_name="name.reference.call"),
    ]
    g = _make_graph(tags)
    unique_edges = [e for e in g.edges if e.reason == "unique-method"]
    assert len(unique_edges) == 0  # two Methods → ambiguous → skip


def test_calls_vs_imports_kind():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="login", line=1, kind="ref",
            capture_name="name.reference.import"),
    ]
    imports = [
        ImportTag(file="views.py", imported_name="login",
                  source_path="auth", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    import_edges = [e for e in g.edges if e.reason == "import-resolved"]
    assert len(import_edges) == 1
    assert import_edges[0].kind == "IMPORTS"


def test_call_ref_kind_is_calls():
    tags = [
        Tag(file="auth.py", name="validate", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="validate", line=5, kind="ref",
            capture_name="name.reference.call"),
    ]
    g = _make_graph(tags)
    call_edges = [e for e in g.edges if e.reason == "global-unique"]
    assert len(call_edges) == 1
    assert call_edges[0].kind == "CALLS"


def test_symbol_context_format():
    tags = [
        Tag(file="auth.py", name="login", line=10, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="login", line=5, kind="ref",
            capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="views.py", imported_name="login",
                  source_path="auth", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    result = g.symbol_context("login")
    assert "login" in result
    assert "auth.py" in result
    assert "Incoming" in result or "Outgoing" in result


def test_unknown_symbol_context():
    g = _make_graph([])
    result = g.symbol_context("nonexistent")
    assert "not found" in result.lower()


def test_format_file_edges():
    tags = [
        Tag(file="auth.py", name="login", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="views.py", name="login", line=5, kind="ref",
            capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="views.py", imported_name="login",
                  source_path="auth", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    result = g.format_file_edges()
    assert "views.py" in result or "auth.py" in result
