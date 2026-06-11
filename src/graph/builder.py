# src/graph/builder.py
"""Build orchestration for RepoGraphLite with caching."""
from __future__ import annotations
import os

from graph.models import ImportTag, TypeBinding, ReceiverTag
from graph.repo_graph import RepoGraphLite
from repo_map import Tag


def build(root_path: str) -> RepoGraphLite:
    """Build a RepoGraphLite from all source files under root_path.

    Uses incremental rebuild when <50% of files changed.
    """
    from graph.graph_store import GraphStore
    from repo_map import _EXT_TO_LANG, _should_include
    from repo_map import _extract_tags_and_receivers
    from graph.import_resolver import extract_imports
    from graph.type_resolver import extract_type_bindings

    if not _should_include(os.path.basename(os.path.abspath(root_path)), is_dir=True):
        return RepoGraphLite()

    store = GraphStore(root_path)
    current_files = _scan_mtimes(root_path)

    stale = store.get_stale_files(current_files)
    if not stale:
        cached = store.load()
        if cached is not None:
            return cached

    # Decide: partial or full rebuild
    cached_graph = store.load() if len(stale) < len(current_files) * 0.5 else None

    if cached_graph is not None:
        # Partial rebuild: remove stale files, re-parse only them
        for filepath in stale:
            cached_graph.remove_file(filepath)

        # Re-parse stale files
        for filepath in stale:
            if filepath not in current_files:
                continue
            if not _path_should_include(root_path, filepath, _should_include):
                continue
            if not os.path.isfile(filepath):
                continue
            ext = os.path.splitext(filepath)[1].lower()
            lang = _EXT_TO_LANG.get(ext)
            if lang is None:
                continue
            tags, receivers = _extract_tags_and_receivers(filepath, lang)
            # Add nodes from new tags
            for t in tags:
                if t.kind == "def":
                    from graph.repo_graph import _tag_kind, _make_node_id
                    from graph.models import SymbolNode
                    nk = _tag_kind(t.capture_name, t.node_type, t.scope)
                    nid = _make_node_id(nk, t.name, t.file, t.scope)
                    if nid not in cached_graph.nodes:
                        node = SymbolNode(
                            id=nid, kind=nk, name=t.name,
                            file=t.file, line=t.line, scope=t.scope,
                            is_exported=False,
                        )
                        cached_graph.nodes[nid] = node
                        cached_graph.by_name[t.name].append(nid)
                        cached_graph.by_file[t.file].append(nid)

        # Full edge rebuild (edges depend on global symbol set)
        all_tags: list[Tag] = []
        all_imports: list[ImportTag] = []
        all_bindings: list[TypeBinding] = []
        all_receivers: list[ReceiverTag] = []

        for dirpath, dirnames, filenames in os.walk(root_path):
            dirnames[:] = [d for d in dirnames if _should_include(d, is_dir=True)]
            for fname in filenames:
                if not _should_include(fname, is_dir=False):
                    continue
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

        # Rebuild edges on the existing graph (nodes already populated)
        cached_graph.edges.clear()
        cached_graph.incoming.clear()
        cached_graph.outgoing.clear()
        cached_graph.build_from(all_tags, all_imports, all_bindings, all_receivers)

        store.save(cached_graph, current_files)
        return cached_graph

    # Full rebuild
    all_tags_full: list[Tag] = []
    all_imports_full: list[ImportTag] = []
    all_bindings_full: list[TypeBinding] = []
    all_receivers_full: list[ReceiverTag] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if _should_include(d, is_dir=True)]
        for fname in filenames:
            if not _should_include(fname, is_dir=False):
                continue
            filepath = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname)[1].lower()
            lang = _EXT_TO_LANG.get(ext)
            if lang is None:
                continue

            if lang == "vue":
                # Vue: extract script, pass bytes to importers/type resolvers
                from vue_utils import extract_vue_script
                result = extract_vue_script(filepath=filepath)
                tags, receivers = _extract_tags_and_receivers(filepath, lang)
                all_tags_full.extend(tags)
                all_receivers_full.extend(receivers)
                if result is not None:
                    script_bytes, actual_lang, line_offset = result
                    imps = extract_imports(filepath, actual_lang, source=script_bytes)
                    for imp in imps:
                        imp.line += line_offset
                    all_imports_full.extend(imps)
                    binds = extract_type_bindings(filepath, actual_lang, source=script_bytes)
                    all_bindings_full.extend(binds)
            else:
                tags, receivers = _extract_tags_and_receivers(filepath, lang)
                all_tags_full.extend(tags)
                all_receivers_full.extend(receivers)
                all_imports_full.extend(extract_imports(filepath, lang))
                all_bindings_full.extend(extract_type_bindings(filepath, lang))

    graph = RepoGraphLite()
    graph.build_from(all_tags_full, all_imports_full, all_bindings_full, all_receivers_full)

    store.save(graph, current_files)
    return graph


def _scan_mtimes(root_path: str) -> dict[str, float]:
    """Walk root_path and collect file modification times."""
    from repo_map import _should_include
    mtimes = {}
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if _should_include(d, is_dir=True)]
        for fname in filenames:
            if not _should_include(fname, is_dir=False):
                continue
            fp = os.path.join(dirpath, fname)
            try:
                mtimes[fp] = os.path.getmtime(fp)
            except OSError:
                pass
    return mtimes


def _path_should_include(root_path: str, filepath: str, should_include) -> bool:
    try:
        relative_path = os.path.relpath(filepath, root_path)
    except ValueError:
        return False
    parts = relative_path.split(os.sep)
    if any(not should_include(part, is_dir=True) for part in parts[:-1]):
        return False
    return bool(parts) and should_include(parts[-1], is_dir=False)
