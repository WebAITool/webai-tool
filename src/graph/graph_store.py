# src/graph/graph_store.py
"""JSON-based persistence for RepoGraphLite."""
from __future__ import annotations
import json
import os
from dataclasses import asdict
from typing import TYPE_CHECKING

from graph.models import SymbolNode, Edge

if TYPE_CHECKING:
    from graph.repo_graph import RepoGraphLite


_CACHE_DIR = ".repo-graph"
_VERSION = 1


class GraphStore:
    def __init__(self, root_path: str) -> None:
        self.cache_dir = os.path.join(root_path, _CACHE_DIR)

    def save(self, graph: "RepoGraphLite", files: dict[str, float]) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)
        meta = {"version": _VERSION, "file_count": len(files)}
        self._write("meta.json", meta)
        self._write("files.json", files)
        self._write("nodes.json", [asdict(n) for n in graph.nodes.values()])
        self._write("edges.json", [asdict(e) for e in graph.edges])

    def load(self) -> "RepoGraphLite | None":
        try:
            nodes_data = self._read("nodes.json")
            edges_data = self._read("edges.json")
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        from graph.repo_graph import RepoGraphLite

        g = RepoGraphLite()

        for d in nodes_data:
            n = SymbolNode(**d)
            g.nodes[n.id] = n
            g.by_name[n.name].append(n.id)
            g.by_file[n.file].append(n.id)

        for d in edges_data:
            e = Edge(**d)
            g.edges.append(e)
            g.incoming[e.target_id].append(e)
            g.outgoing[e.source_id].append(e)

        return g

    def get_stale_files(self, current_files: dict[str, float]) -> set[str]:
        """Return files whose mtime changed, were added, or were removed."""
        try:
            cached_files: dict[str, float] = self._read("files.json")
        except (FileNotFoundError, json.JSONDecodeError):
            return set(current_files.keys())

        stale: set[str] = set()
        for path, mtime in current_files.items():
            if path not in cached_files or cached_files[path] != mtime:
                stale.add(path)
        for path in cached_files:
            if path not in current_files:
                stale.add(path)
        return stale

    def is_stale(self, current_files: dict[str, float]) -> bool:
        try:
            cached_files: dict[str, float] = self._read("files.json")
        except (FileNotFoundError, json.JSONDecodeError):
            return True
        return cached_files != current_files

    def _write(self, filename: str, data) -> None:
        path = os.path.join(self.cache_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _read(self, filename: str):
        path = os.path.join(self.cache_dir, filename)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
