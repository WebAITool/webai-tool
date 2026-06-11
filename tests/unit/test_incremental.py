# tests/unit/test_incremental.py
"""Tests for incremental reindex support."""
import json
import os
import time
from dataclasses import asdict

from graph.builder import build
from graph.graph_store import GraphStore
from graph.models import ImportTag, SymbolNode
from graph.repo_graph import RepoGraphLite
from repo_map import Tag


def test_get_stale_files_no_cache(tmp_path):
    """No cache → all files are stale."""
    store = GraphStore(str(tmp_path))
    current = {"a.py": 1.0, "b.py": 2.0}
    stale = store.get_stale_files(current)
    assert stale == {"a.py", "b.py"}


def test_get_stale_files_unchanged(tmp_path):
    """All mtimes match → no stale files."""
    store = GraphStore(str(tmp_path))
    files = {"a.py": 1.0, "b.py": 2.0}
    # Manually write cache
    cache_dir = os.path.join(str(tmp_path), ".repo-graph")
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "files.json"), "w") as f:
        json.dump(files, f)
    stale = store.get_stale_files(files)
    assert stale == set()


def test_get_stale_files_changed(tmp_path):
    """One file changed → only that file is stale."""
    store = GraphStore(str(tmp_path))
    cached = {"a.py": 1.0, "b.py": 2.0}
    cache_dir = os.path.join(str(tmp_path), ".repo-graph")
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "files.json"), "w") as f:
        json.dump(cached, f)
    current = {"a.py": 1.0, "b.py": 3.0}  # b.py changed
    stale = store.get_stale_files(current)
    assert stale == {"b.py"}


def test_get_stale_files_added(tmp_path):
    """New file added → it's stale."""
    store = GraphStore(str(tmp_path))
    cached = {"a.py": 1.0}
    cache_dir = os.path.join(str(tmp_path), ".repo-graph")
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "files.json"), "w") as f:
        json.dump(cached, f)
    current = {"a.py": 1.0, "c.py": 4.0}
    stale = store.get_stale_files(current)
    assert stale == {"c.py"}


def test_get_stale_files_removed(tmp_path):
    """File removed → it's stale (need to clean its nodes)."""
    store = GraphStore(str(tmp_path))
    cached = {"a.py": 1.0, "b.py": 2.0}
    cache_dir = os.path.join(str(tmp_path), ".repo-graph")
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "files.json"), "w") as f:
        json.dump(cached, f)
    current = {"a.py": 1.0}  # b.py removed
    stale = store.get_stale_files(current)
    assert stale == {"b.py"}


def _make_graph(tags, imports=None, bindings=None, receivers=None):
    g = RepoGraphLite()
    g.build_from(tags, imports or [], bindings or [], receivers or [])
    return g


def test_remove_file_cleans_nodes():
    """remove_file removes all nodes for that file."""
    tags = [
        Tag(file="a.py", name="func_a", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="b.py", name="func_b", line=1, kind="def",
            capture_name="name.definition.function"),
    ]
    g = _make_graph(tags)
    assert any(n.file == "a.py" for n in g.nodes.values())
    g.remove_file("a.py")
    assert not any(n.file == "a.py" for n in g.nodes.values())
    assert any(n.file == "b.py" for n in g.nodes.values())


def test_remove_file_cleans_edges():
    """remove_file removes edges involving that file."""
    tags = [
        Tag(file="a.py", name="func_a", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="b.py", name="func_b", line=1, kind="def",
            capture_name="name.definition.function"),
        Tag(file="b.py", name="func_a", line=5, kind="ref",
            scope="func_b", capture_name="name.reference.call"),
    ]
    imports = [
        ImportTag(file="b.py", imported_name="func_a",
                  source_path="a", is_relative=False, line=1),
    ]
    g = _make_graph(tags, imports=imports)
    assert len(g.edges) > 0
    g.remove_file("a.py")
    # Edges referencing a.py nodes should be gone
    for e in g.edges:
        assert "a.py" not in e.source_id
        assert "a.py" not in e.target_id


def test_remove_file_cleans_indexes():
    """remove_file cleans by_name, by_file, incoming, outgoing."""
    tags = [
        Tag(file="a.py", name="func_a", line=1, kind="def",
            capture_name="name.definition.function"),
    ]
    g = _make_graph(tags)
    assert "a.py" in g.by_file
    g.remove_file("a.py")
    assert "a.py" not in g.by_file
    assert "func_a" not in g.by_name or not g.by_name["func_a"]


def test_partial_rebuild(tmp_path):
    """Changing one file only re-parses that file, not the whole project."""
    # Create 2 files
    (tmp_path / "a.py").write_text("def func_a(): pass\n")
    (tmp_path / "b.py").write_text("def func_b(): pass\n")

    # First build — full
    g1 = build(str(tmp_path))
    assert "func_a" in [n.name for n in g1.nodes.values()]
    assert "func_b" in [n.name for n in g1.nodes.values()]

    # Modify only b.py
    time.sleep(0.1)  # ensure different mtime
    (tmp_path / "b.py").write_text("def func_b_v2(): pass\n")

    # Second build — should partial rebuild
    g2 = build(str(tmp_path))
    names = [n.name for n in g2.nodes.values()]
    assert "func_a" in names  # unchanged file preserved
    assert "func_b_v2" in names  # changed file re-parsed
    assert "func_b" not in names  # old symbol gone


def test_partial_rebuild_drops_legacy_env_cache_nodes(tmp_path):
    """Old cached .env* symbols must be removed, not re-parsed."""
    public_files = []
    for index in range(8):
        path = tmp_path / f"public_{index}.py"
        path.write_text(f"def public_{index}(): pass\n", encoding="utf-8")
        public_files.append(path)

    secret_dir = tmp_path / ".env.secrets"
    secret_dir.mkdir()
    secret_file = secret_dir / "secret_token.py"
    secret_file.write_text("def leaked_secret_symbol(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / ".repo-graph"
    cache_dir.mkdir()
    cached_files = {str(path): os.path.getmtime(path) for path in public_files}
    cached_files[str(secret_file)] = os.path.getmtime(secret_file)
    leaked_node = SymbolNode(
        id=f"Function:leaked_secret_symbol:{secret_file}",
        kind="Function",
        name="leaked_secret_symbol",
        file=str(secret_file),
        line=1,
        scope="",
        is_exported=False,
    )
    (cache_dir / "files.json").write_text(json.dumps(cached_files), encoding="utf-8")
    (cache_dir / "nodes.json").write_text(
        json.dumps([asdict(leaked_node)]),
        encoding="utf-8",
    )
    (cache_dir / "edges.json").write_text("[]", encoding="utf-8")

    graph = build(str(tmp_path))
    names = [node.name for node in graph.nodes.values()]
    node_files = [node.file for node in graph.nodes.values()]
    files_json = (cache_dir / "files.json").read_text(encoding="utf-8")

    assert "leaked_secret_symbol" not in names
    assert str(secret_file) not in node_files
    assert ".env.secrets" not in files_json


def test_build_ignores_env_directory_root(tmp_path):
    root = tmp_path / ".env.secrets"
    root.mkdir()
    (root / "secret_token.py").write_text(
        "def leaked_secret_symbol(): pass\n",
        encoding="utf-8",
    )

    graph = build(str(root))

    assert not graph.nodes
    assert not (root / ".repo-graph").exists()
