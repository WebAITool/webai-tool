# src/graph/repo_graph.py
"""RepoGraphLite — symbol-level cross-file reference graph."""
from __future__ import annotations
import os
from collections import defaultdict

from graph.models import SymbolNode, Edge, ImportTag, TypeBinding, ReceiverTag
from repo_map import Tag


# Minimum symbol name length to avoid noise
_MIN_LEN = 3


def _make_node_id(kind: str, name: str, file: str, scope: str = "") -> str:
    if kind == "Method" and scope:
        return f"Method:{name}@{scope}:{file}"
    return f"{kind}:{name}:{file}"


def _tag_kind(capture_name: str, node_type: str, scope: str) -> str:
    """Determine SymbolNode.kind from capture name and node type."""
    if ".definition.class" in capture_name or ".definition.interface" in capture_name:
        if node_type == "interface_declaration":
            return "Interface"
        return "Class"
    if ".definition.function" in capture_name:
        if scope:
            return "Method"
        return "Function"
    return "Function"


def _edge_kind(capture_name: str) -> str:
    """Determine Edge.kind from the ref Tag's capture_name."""
    if ".reference.import" in capture_name:
        return "IMPORTS"
    return "CALLS"


class RepoGraphLite:
    """Symbol-level directed code graph."""

    def __init__(self) -> None:
        self.nodes: dict[str, SymbolNode] = {}
        self.edges: list[Edge] = []
        self.incoming: dict[str, list[Edge]] = defaultdict(list)
        self.outgoing: dict[str, list[Edge]] = defaultdict(list)
        self.by_name: dict[str, list[str]] = defaultdict(list)
        self.by_file: dict[str, list[str]] = defaultdict(list)

    def build_from(
        self,
        tags: list[Tag],
        imports: list[ImportTag],
        bindings: list[TypeBinding],
        receivers: list[ReceiverTag],
    ) -> None:
        """Build graph from extracted data."""
        # Build import lookup: (file, imported_name) → resolved_file
        import_map: dict[tuple[str, str], str] = {}
        all_files = list({t.file for t in tags})
        from graph.import_resolver import build_suffix_index, resolve_import
        suffix_index = build_suffix_index(all_files)
        for imp in imports:
            resolved = resolve_import(imp.source_path, imp.file, suffix_index)
            if resolved:
                import_map[(imp.file, imp.imported_name)] = resolved

        # Build type binding lookup: (file, scope, var_name) → resolved_type
        binding_map: dict[tuple[str, str, str], str] = {}
        for b in bindings:
            binding_map[(b.file, b.scope, b.var_name)] = b.resolved_type

        # Build receiver lookup: (file, scope, method_name) → receiver_name
        receiver_map: dict[tuple[str, str, str], str] = {}
        for r in receivers:
            receiver_map[(r.file, r.scope, r.method_name)] = r.receiver_name

        # Create SymbolNodes from def tags
        for t in tags:
            if t.kind != "def" or len(t.name) < _MIN_LEN:
                continue
            kind = _tag_kind(t.capture_name, t.node_type, t.scope)
            node_id = _make_node_id(kind, t.name, t.file, t.scope)
            if node_id not in self.nodes:
                node = SymbolNode(
                    id=node_id, kind=kind, name=t.name,
                    file=t.file, line=t.line, scope=t.scope,
                    is_exported=False,
                )
                self.nodes[node_id] = node
                self.by_name[t.name].append(node_id)
                self.by_file[t.file].append(node_id)

        # Resolve ref tags → edges
        for t in tags:
            if t.kind != "ref" or len(t.name) < _MIN_LEN:
                continue
            edge = self._resolve_ref(t, import_map, binding_map, receiver_map)
            if edge:
                self.edges.append(edge)
                self.incoming[edge.target_id].append(edge)
                self.outgoing[edge.source_id].append(edge)

    def _resolve_ref(
        self,
        ref: Tag,
        import_map: dict,
        binding_map: dict,
        receiver_map: dict,
    ) -> Edge | None:
        """Apply priority table to resolve a ref tag to an Edge."""
        name = ref.name
        candidates = self.by_name.get(name, [])

        # Find source node (the function/method containing this ref)
        source_ids = self.by_file.get(ref.file, [])
        source_id = next(
            (nid for nid in source_ids
             if self.nodes[nid].name == ref.scope),
            f"File:{ref.file}",  # fallback: file-level source
        )

        def make_edge(target_id: str, conf: float, reason: str) -> Edge:
            return Edge(
                source_id=source_id,
                target_id=target_id,
                kind=_edge_kind(ref.capture_name),
                confidence=conf,
                reason=reason,
            )

        # Priority 1: self/this access
        recv = receiver_map.get((ref.file, ref.scope, name))
        if recv in ("self", "this"):
            # ref.scope is the enclosing METHOD name; find its enclosing CLASS
            enclosing_class = None
            for nid in self.by_file.get(ref.file, []):
                n = self.nodes[nid]
                if n.name == ref.scope and n.scope:  # find the enclosing method def
                    enclosing_class = n.scope
                    break
            if enclosing_class:
                for nid in candidates:
                    n = self.nodes[nid]
                    if n.file == ref.file and n.scope == enclosing_class:
                        return make_edge(nid, 1.0, "self-access")

        # Priority 2: same-file def
        same_file = [nid for nid in candidates if self.nodes[nid].file == ref.file]
        if len(same_file) == 1:
            return make_edge(same_file[0], 1.0, "same-file")

        # Priority 3: import-resolved
        resolved_file = import_map.get((ref.file, name))
        if resolved_file:
            for nid in candidates:
                if self.nodes[nid].file == resolved_file:
                    return make_edge(nid, 0.95, "import-resolved")

        # Priority 4: type-resolved method call
        if recv:
            type_name = binding_map.get((ref.file, ref.scope, recv))
            if type_name:
                for nid in candidates:
                    n = self.nodes[nid]
                    if n.scope == type_name or (n.kind == "Method" and type_name in n.id):
                        return make_edge(nid, 0.9, "type-resolved")

        # Priority 5: scope match — exactly one def in same enclosing class
        scope_match = [nid for nid in candidates
                       if self.nodes[nid].scope == ref.scope and ref.scope]
        if len(scope_match) == 1:
            return make_edge(scope_match[0], 0.85, "scope-match")

        # Priority 6: single global def
        if len(candidates) == 1:
            return make_edge(candidates[0], 0.7, "global-unique")

        # Priority 7: single class has this method
        method_defs = [nid for nid in candidates if self.nodes[nid].kind == "Method"]
        if len(method_defs) == 1:
            return make_edge(method_defs[0], 0.5, "unique-method")

        # Ambiguous → skip
        return None

    def symbol_context(self, name: str, file: str | None = None) -> str:
        """Return formatted 360° view of a symbol."""
        candidates = self.by_name.get(name, [])
        if not candidates:
            return f"Symbol '{name}' not found in definitions."

        if file:
            candidates = [nid for nid in candidates if file in self.nodes[nid].file]
        if not candidates:
            return f"Symbol '{name}' not found in file '{file}'."

        node = self.nodes[candidates[0]]
        lines = [f"=== {node.kind} {node.name} ({node.file}:{node.line}) ===", ""]

        inc = sorted(self.incoming.get(node.id, []),
                     key=lambda e: (-e.confidence, e.source_id))
        if inc:
            lines.append("Incoming (who calls/imports this):")
            for e in inc:
                src = self.nodes.get(e.source_id)
                src_str = f"{src.name} ({src.file}:{src.line})" if src else e.source_id
                lines.append(f"  {e.kind}: {src_str} [{e.confidence:.2f} {e.reason}]")
            lines.append("")

        out = sorted(self.outgoing.get(node.id, []),
                     key=lambda e: (-e.confidence, e.target_id))
        if out:
            lines.append("Outgoing (what this calls/uses):")
            for e in out:
                tgt = self.nodes.get(e.target_id)
                tgt_str = f"{tgt.name} ({tgt.file}:{tgt.line})" if tgt else e.target_id
                lines.append(f"  {e.kind}: {tgt_str} [{e.confidence:.2f} {e.reason}]")

        return "\n".join(lines)

    def symbol_graph(self, name: str, depth: int = 1) -> str:
        """BFS symbol dependency graph."""
        candidates = self.by_name.get(name, [])
        if not candidates:
            return f"Symbol '{name}' not found in definitions."
        node = self.nodes[candidates[0]]
        lines = [f"=== {name} (defined in {node.file}) ===", ""]

        visited: set[str] = {node.id}
        frontier = [(node.id, 0)]
        uses_lines: list[str] = []
        while frontier:
            cur_id, cur_depth = frontier.pop(0)
            if cur_depth >= depth:
                continue
            for e in self.outgoing.get(cur_id, []):
                if e.target_id not in visited:
                    visited.add(e.target_id)
                    tgt = self.nodes.get(e.target_id)
                    if tgt:
                        uses_lines.append(
                            f"  depth {cur_depth + 1}: {tgt.name} ({tgt.file})"
                        )
                        frontier.append((e.target_id, cur_depth + 1))

        if uses_lines:
            lines.append("Uses (what it calls):")
            lines.extend(uses_lines)

        return "\n".join(lines)

    def impact(self, name: str, direction: str = "upstream",
               max_depth: int = 3, min_confidence: float = 0.7,
               file: str | None = None) -> str:
        """BFS blast radius analysis for a symbol."""
        candidates = self.by_name.get(name, [])
        if not candidates:
            return f"Symbol '{name}' not found in definitions."

        if file:
            candidates = [nid for nid in candidates if file in self.nodes[nid].file]
        if not candidates:
            return f"Symbol '{name}' not found in file '{file}'."

        node = self.nodes[candidates[0]]
        edge_index = self.incoming if direction == "upstream" else self.outgoing
        dir_label = "UPSTREAM (what depends on this)" if direction == "upstream" \
            else "DOWNSTREAM (what this depends on)"

        depth_labels = {1: "WILL BREAK", 2: "LIKELY AFFECTED"}

        visited: set[str] = {node.id}
        frontier: list[tuple[str, int]] = [(node.id, 0)]
        by_depth: dict[int, list[str]] = {}

        while frontier:
            cur_id, cur_depth = frontier.pop(0)
            if cur_depth >= max_depth:
                continue
            for e in edge_index.get(cur_id, []):
                peer_id = e.source_id if direction == "upstream" else e.target_id
                if peer_id in visited or e.confidence < min_confidence:
                    continue
                visited.add(peer_id)
                peer = self.nodes.get(peer_id)
                if peer:
                    d = cur_depth + 1
                    label = depth_labels.get(d, "MAY NEED TESTING")
                    line = f"    {peer.name} ({peer.file}:{peer.line}) [{e.kind} {e.confidence:.2f}]"
                    by_depth.setdefault(d, []).append((label, line))
                    frontier.append((peer_id, d))

        lines = [f"TARGET: {node.kind} {node.name} ({node.file}:{node.line})", ""]
        if not by_depth:
            lines.append(f"{dir_label}:\n  (none)")
        else:
            lines.append(f"{dir_label}:")
            for d in sorted(by_depth):
                label = by_depth[d][0][0]
                lines.append(f"  Depth {d} — {label}:")
                for _, entry in by_depth[d]:
                    lines.append(entry)

        depth1_count = len(by_depth.get(1, []))
        deeper_files = len({self.nodes[vid].file for vid in visited
                           if vid != node.id and vid in self.nodes} - {node.file})
        lines.append("")
        lines.append(f"Summary: {depth1_count} direct callers, {deeper_files} files at depth 2+")

        if depth1_count > 5:
            risk = "HIGH"
        elif depth1_count >= 2:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        lines.append(f"Risk: {risk}")

        return "\n".join(lines)

    def _node_file(self, node_id: str) -> str | None:
        """Return the file for a node_id, handling both real nodes and 'File:...' fallbacks."""
        node = self.nodes.get(node_id)
        if node:
            return node.file
        if node_id.startswith("File:"):
            return node_id[len("File:"):]
        return None

    def format_file_edges(self, root_path: str | None = None) -> str:
        """File-level edge summary (replaces old format_section for show_references)."""
        file_edges: dict[tuple[str, str], list[str]] = defaultdict(list)
        for e in self.edges:
            src_file = self._node_file(e.source_id)
            tgt_node = self.nodes.get(e.target_id)
            if src_file and tgt_node and src_file != tgt_node.file:
                key = (src_file, tgt_node.file)
                # Use target name for file-level fallback sources, source node name otherwise
                src_node = self.nodes.get(e.source_id)
                label = src_node.name if src_node else tgt_node.name
                file_edges[key].append(label)

        if not file_edges:
            return ""

        def rel(p: str) -> str:
            if root_path:
                try:
                    return os.path.relpath(p, root_path)
                except ValueError:
                    pass
            return p

        lines = ["", "References:"]
        for (src_f, tgt_f), names in sorted(file_edges.items()):
            unique = sorted(set(names))
            lines.append(f"  {rel(src_f)} -> {rel(tgt_f)} via: {', '.join(unique)}")
        return "\n".join(lines)
