# src/graph/builder.py
"""Build orchestration for RepoGraphLite with caching."""
from __future__ import annotations
import os

from graph.models import ImportTag, TypeBinding, ReceiverTag
from graph.repo_graph import RepoGraphLite
from repo_map import Tag


def build(root_path: str) -> RepoGraphLite:
    """Build a RepoGraphLite from all source files under root_path."""
    from graph.graph_store import GraphStore
    from repo_map import IGNORED_DIRS, _EXT_TO_LANG
    from repo_map import _extract_tags_and_receivers
    from graph.import_resolver import extract_imports
    from graph.type_resolver import extract_type_bindings

    store = GraphStore(root_path)
    current_files = _scan_mtimes(root_path)

    if not store.is_stale(current_files):
        cached = store.load()
        if cached is not None:
            return cached

    all_tags: list[Tag] = []
    all_imports: list[ImportTag] = []
    all_bindings: list[TypeBinding] = []
    all_receivers: list[ReceiverTag] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fname in filenames:
            filepath = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname)[1].lower()
            lang = _EXT_TO_LANG.get(ext)
            if lang is None:
                continue
            tags, receivers = _extract_tags_and_receivers(filepath, lang)
            all_tags.extend(tags)
            all_receivers.extend(receivers)
            all_imports.extend(extract_imports(filepath, lang))
            all_bindings.extend(extract_type_bindings(filepath, lang))

    graph = RepoGraphLite()
    graph.build_from(all_tags, all_imports, all_bindings, all_receivers)

    store.save(graph, current_files)
    return graph


def _scan_mtimes(root_path: str) -> dict[str, float]:
    """Walk root_path and collect file modification times."""
    from repo_map import IGNORED_DIRS
    mtimes = {}
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fname in filenames:
            fp = os.path.join(dirpath, fname)
            try:
                mtimes[fp] = os.path.getmtime(fp)
            except OSError:
                pass
    return mtimes
