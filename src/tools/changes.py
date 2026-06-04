# src/tools/changes.py
"""LangChain tool for detecting git changes and mapping to affected symbols."""
from __future__ import annotations
import os
import subprocess
from bisect import bisect_right
from langchain_core.tools import tool

from graph.builder import build
from graph.models import SymbolNode


def _parse_diff(diff_text: str) -> dict[str, set[int]]:
    """Parse unified diff output into {file: set of changed line numbers}."""
    result: dict[str, set[int]] = {}
    current_file: str | None = None
    current_line = 0

    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            current_file = line[6:]
            if current_file not in result:
                result[current_file] = set()
        elif line.startswith("@@ "):
            parts = line.split(" ")
            for part in parts:
                if part.startswith("+") and "," in part:
                    current_line = int(part.split(",")[0][1:])
                    break
                elif part.startswith("+") and part[1:].isdigit():
                    current_line = int(part[1:])
                    break
        elif current_file is not None:
            if line.startswith("+") and not line.startswith("+++"):
                result[current_file].add(current_line)
                current_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                pass
            else:
                current_line += 1

    return result


def _map_lines_to_symbols(
    changed_lines: set[int],
    symbols: list[SymbolNode],
) -> list[SymbolNode]:
    """Map changed lines to symbols using nearest-preceding-def heuristic."""
    if not symbols or not changed_lines:
        return []

    sorted_symbols = sorted(symbols, key=lambda s: s.line)
    start_lines = [s.line for s in sorted_symbols]

    matched: set[str] = set()
    result: list[SymbolNode] = []

    for line in changed_lines:
        idx = bisect_right(start_lines, line) - 1
        if idx >= 0:
            sym = sorted_symbols[idx]
            if sym.id not in matched:
                matched.add(sym.id)
                result.append(sym)

    return result


@tool
def detect_changes(
    scope: str = "unstaged",
    root_path: str | None = None,
) -> str:
    """Map git changes to affected symbols and show blast radius.

    Args:
        scope: "unstaged" | "staged" | "all" (default "unstaged")
        root_path: Project root directory (defaults to current directory)
    """
    root = root_path or os.getcwd()

    if scope == "staged":
        cmd = ["git", "diff", "--cached"]
    elif scope == "all":
        cmd = ["git", "diff", "HEAD"]
    else:
        cmd = ["git", "diff"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", cwd=root,
        )
    except FileNotFoundError:
        return "Error: git not found"

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "not a git repository" in stderr:
            return "Error: not a git repository"
        return f"Error: git diff failed: {stderr}"

    diff_text = result.stdout
    if not diff_text.strip():
        return "No changes detected"

    file_lines = _parse_diff(diff_text)
    if not file_lines:
        return "No changes detected"

    graph = build(root)
    output_lines: list[str] = [f"Changed symbols ({scope}):"]
    total_symbols = 0
    total_callers = 0

    for file, changed in sorted(file_lines.items()):
        # Normalize to match graph.by_file keys: os.walk produces
        # OS-native paths (backslashes on Windows, with root prefix)
        lookup = os.path.normpath(os.path.join(root, file))
        node_ids = next(
            (ids for key, ids in graph.by_file.items()
             if os.path.normpath(key) == lookup),
            [],
        )
        if not node_ids:
            continue
        file_symbols = [graph.nodes[nid] for nid in node_ids]
        affected = _map_lines_to_symbols(changed, file_symbols)

        for sym in affected:
            total_symbols += 1
            display = f"{sym.name}@{sym.scope}" if sym.kind == "Method" and sym.scope else sym.name
            output_lines.append(f"  {sym.kind} {display} ({sym.file}:{sym.line})")

            callers = [
                e for e in graph.incoming.get(sym.id, [])
                if e.confidence >= 0.7
            ]
            if callers:
                caller_strs = []
                for e in callers:
                    src = graph.nodes.get(e.source_id)
                    if src:
                        caller_strs.append(f"{src.name} ({src.file}:{src.line})")
                    else:
                        caller_strs.append(e.source_id)
                total_callers += len(caller_strs)
                output_lines.append(f"    \u2191 callers: {', '.join(caller_strs)}")

    if total_symbols == 0:
        return "No changes detected in tracked symbols"

    output_lines.append("")
    output_lines.append(f"Summary: {total_symbols} symbols changed, {total_callers} callers affected")
    return "\n".join(output_lines)
