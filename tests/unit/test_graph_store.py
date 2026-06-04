import os, tempfile, time
from graph.graph_store import GraphStore
from graph.repo_graph import RepoGraphLite
from graph.models import SymbolNode, Edge
from repo_map import Tag


def _make_simple_graph() -> RepoGraphLite:
    g = RepoGraphLite()
    g.build_from(
        [Tag(file="auth.py", name="login", line=1, kind="def",
             capture_name="name.definition.function")],
        [], [], []
    )
    return g


def test_save_and_load():
    with tempfile.TemporaryDirectory() as root:
        store = GraphStore(root)
        graph = _make_simple_graph()
        files = {"auth.py": 1000.0}
        store.save(graph, files)
        loaded = store.load()
        assert loaded is not None
        assert "login" in loaded.by_name


def test_not_stale_when_unchanged():
    with tempfile.TemporaryDirectory() as root:
        store = GraphStore(root)
        files = {"auth.py": 1000.0}
        store.save(_make_simple_graph(), files)
        assert not store.is_stale(files)


def test_stale_when_file_changed():
    with tempfile.TemporaryDirectory() as root:
        store = GraphStore(root)
        files_old = {"auth.py": 1000.0}
        store.save(_make_simple_graph(), files_old)
        files_new = {"auth.py": 2000.0}  # mtime changed
        assert store.is_stale(files_new)


def test_stale_when_file_added():
    with tempfile.TemporaryDirectory() as root:
        store = GraphStore(root)
        store.save(_make_simple_graph(), {"auth.py": 1000.0})
        assert store.is_stale({"auth.py": 1000.0, "views.py": 1001.0})


def test_stale_when_no_cache():
    with tempfile.TemporaryDirectory() as root:
        store = GraphStore(root)
        assert store.is_stale({"auth.py": 1000.0})


def test_load_returns_none_when_no_cache():
    with tempfile.TemporaryDirectory() as root:
        store = GraphStore(root)
        assert store.load() is None
