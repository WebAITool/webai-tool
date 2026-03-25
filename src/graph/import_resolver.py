# src/graph/import_resolver.py
"""Import extraction and path resolution for the symbol graph."""
from __future__ import annotations
import os
from pathlib import Path

from graph.models import ImportTag


_QUERY_CACHE: dict[str, str | None] = {}


def _load_import_query(lang: str) -> str | None:
    if lang in _QUERY_CACHE:
        return _QUERY_CACHE[lang]
    # tsx uses typescript imports
    scm_lang = "typescript" if lang == "tsx" else lang
    scm_path = os.path.join(
        os.path.dirname(__file__), "..", "queries", f"{scm_lang}-imports.scm"
    )
    try:
        with open(os.path.normpath(scm_path)) as f:
            text = f.read()
    except FileNotFoundError:
        _QUERY_CACHE[lang] = None
        return None
    _QUERY_CACHE[lang] = text
    return text


def extract_imports(filepath: str, lang: str, source: bytes | None = None) -> list[ImportTag]:
    """Extract ImportTag list from a source file using language-specific .scm queries."""
    from tree_sitter import Query, QueryCursor
    from tree_sitter_language_pack import get_language, get_parser

    scm_text = _load_import_query(lang)
    if scm_text is None:
        return []

    if source is None:
        try:
            with open(filepath, "rb") as f:
                source = f.read()
        except OSError:
            return []

    try:
        parser = get_parser(lang)
        ts_lang = get_language(lang)
    except Exception:
        return []

    tree = parser.parse(source)
    query = Query(ts_lang, scm_text)
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    # Pair up @import.source and @import.name by line proximity
    sources: list[tuple[int, str]] = []   # (line, source_path)
    names: list[tuple[int, str]] = []     # (line, imported_name)

    for cap_name, nodes in captures.items():
        for node in nodes:
            text = node.text.decode("utf-8", errors="replace").strip("'\"")
            line = node.start_point[0] + 1
            if cap_name == "import.source":
                sources.append((line, text))
            elif cap_name == "import.name":
                names.append((line, text))

    # Match each name to closest preceding source on same import statement
    tags: list[ImportTag] = []
    for name_line, name in names:
        best_src = None
        best_dist = float("inf")
        for src_line, src in sources:
            dist = name_line - src_line
            if 0 <= dist < best_dist:
                best_dist = dist
                best_src = src
        if best_src is not None:
            is_relative = best_src.startswith(".")
            tags.append(ImportTag(
                file=filepath,
                imported_name=name,
                source_path=best_src,
                is_relative=is_relative,
                line=name_line,
            ))

    return tags


def build_suffix_index(all_files: list[str]) -> dict[str, list[str]]:
    """Build a suffix index: normalized_path_without_ext -> [full_paths].

    Also indexes .vue files with extension preserved for Vue import resolution.
    """
    index: dict[str, list[str]] = {}
    for f in all_files:
        p = Path(f)
        # Standard: strip extension
        p_no_ext = p.with_suffix("")
        parts = p_no_ext.parts
        for i in range(len(parts)):
            suffix = "/".join(parts[i:])
            index.setdefault(suffix, []).append(f)
        # Also index with .vue extension preserved
        if p.suffix == ".vue":
            parts_vue = p.parts
            for i in range(len(parts_vue)):
                suffix = "/".join(parts_vue[i:])
                index.setdefault(suffix, []).append(f)
    return index


def resolve_import(
    source_path: str,
    from_file: str,
    suffix_index: dict[str, list[str]],
) -> str | None:
    """Resolve an import source path to an actual file path.

    Returns None for stdlib/node_modules/unresolvable imports.
    """
    # Normalize: strip quotes
    normalized = source_path.strip("'\"")

    # Relative path: resolve relative to from_file's directory
    if normalized.startswith("."):
        base_dir = str(Path(from_file).parent)
        resolved = str(Path(base_dir) / normalized)

        # Try with original extension first (for .vue imports)
        resolved_orig = os.path.normpath(resolved).replace("\\", "/")
        parts_orig = Path(resolved_orig).parts
        for i in range(len(parts_orig)):
            suffix = "/".join(parts_orig[i:])
            if suffix in suffix_index:
                return _pick_closest(suffix_index[suffix], from_file)

        # Fallback: strip extension
        normalized = os.path.normpath(str(Path(resolved).with_suffix("")))
        normalized = normalized.replace("\\", "/")  # Windows -> forward slashes
        parts = Path(normalized).parts
        for i in range(len(parts)):
            suffix = "/".join(parts[i:])
            if suffix in suffix_index:
                candidates = suffix_index[suffix]
                return _pick_closest(candidates, from_file)
        return None

    # Python dotted: "auth.service" -> "auth/service"
    normalized = normalized.replace(".", "/")

    candidates = suffix_index.get(normalized, [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return _pick_closest(candidates, from_file)


def _pick_closest(candidates: list[str], from_file: str) -> str:
    """Pick the candidate file closest to from_file by shared directory depth."""
    from_dir = Path(from_file).parent

    def score(candidate: str) -> int:
        """Return number of shared directory components (higher = closer)."""
        try:
            common = Path(os.path.commonpath([str(from_dir), str(Path(candidate).parent)]))
            return len(Path(common).parts)
        except ValueError:
            return -1

    return max(candidates, key=score)
