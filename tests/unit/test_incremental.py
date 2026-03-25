# tests/unit/test_incremental.py
"""Tests for incremental reindex support."""
import os
import json
from graph.graph_store import GraphStore


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


from graph.repo_graph import RepoGraphLite
from graph.models import ImportTag
from repo_map import Tag


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


import time
from graph.builder import build


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
