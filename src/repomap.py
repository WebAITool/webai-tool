"""
repo_map.py — Repository Map Generator for WebAI Toolkit.

Generates a tree-like map of a project's file structure with code
analysis (classes, functions, methods, etc.) powered by tree-sitter.
Supports Python, JavaScript, TypeScript, and Vue out of the box.
"""

import os
from dataclasses import dataclass

from langchain_core.tools import tool
from tree_sitter_language_pack import SupportedLanguage, get_language, get_parser


@dataclass
class _ReceiverTag:
    """Method call receiver (e.g. 'self' in self.validate())."""
    file: str
    receiver_name: str
    method_name: str
    line: int
    scope: str


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 512 * 1024  # 512 KB — skip files larger than this
MAX_DIR_DEPTH = 30  # max directory nesting depth to prevent infinite recursion
MAX_OUTPUT_LINES = 5000  # truncate output to prevent context window overflow

IGNORED_DIRS = {
    ".git",
    ".repo-graph",
    "__pycache__",
    "node_modules",
    "dist",
    "venv",
    ".venv",
    ".env",
    ".idea",
    ".vscode",
}

IGNORED_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}

IGNORED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".bmp",
    ".webp",
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".mp3",
    ".wav",
    ".ogg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pyc",
    ".pyo",
}


@dataclass
class Tag:
    file: str
    name: str
    line: int
    kind: str           # "def" | "ref"
    scope: str = ""     # enclosing function/class name
    node_type: str = "" # tree-sitter node type (e.g. "interface_declaration")
    capture_name: str = "" # full capture name (e.g. "name.definition.class")


# ---------------------------------------------------------------------------
# Extension → tree-sitter language mapping
# ---------------------------------------------------------------------------

_EXT_TO_LANG: dict[str, SupportedLanguage] = {
    # Python
    ".py": "python",
    ".pyw": "python",
    # JavaScript / TypeScript
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    # Vue
    ".vue": "vue",
}


# ---------------------------------------------------------------------------
# .scm query-based tag extraction
# ---------------------------------------------------------------------------

_QUERY_CACHE: dict[str, str | None] = {}


def _load_query(lang: str) -> str | None:
    """Load .scm query file for the given language. Returns None if not found."""
    if lang in _QUERY_CACHE:
        return _QUERY_CACHE[lang]
    scm_path = os.path.join(os.path.dirname(__file__), "queries", f"{lang}-tags.scm")
    try:
        with open(scm_path, "r") as f:
            text = f.read()
    except FileNotFoundError:
        _QUERY_CACHE[lang] = None
        return None
    _QUERY_CACHE[lang] = text
    return text


def _find_scope(node, root) -> str:
    """Walk up from node to find nearest enclosing function/class name."""
    current = node.parent
    scope_types = {"function_definition", "class_definition",
                   "function_declaration", "class_declaration",
                   "method_definition", "arrow_function"}
    while current and current != root:
        if current.type in scope_types:
            name_node = current.child_by_field_name("name")
            if name_node:
                if name_node == node:
                    current = current.parent
                    continue
                return name_node.text.decode("utf-8", errors="replace")
        current = current.parent
    return ""


def _extract_tags_and_receivers(
    filepath: str, lang: str
) -> tuple[list[Tag], list[_ReceiverTag]]:
    """Extract Tags and ReceiverTags from a file using .scm queries."""
    from tree_sitter import Query, QueryCursor

    try:
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            return [], []
        with open(filepath, "rb") as f:
            source = f.read()
    except OSError:
        return [], []

    # Vue SFC: extract script block, parse as JS/TS, add template refs
    if lang == "vue":
        from vue_utils import extract_vue_script, extract_vue_template_refs

        result = extract_vue_script(filepath=filepath)
        if result is None:
            return [], []
        script_bytes, actual_lang, line_offset = result

        scm_text = _load_query(actual_lang)
        if scm_text is None:
            return [], []

        try:
            parser = get_parser(actual_lang)
            ts_lang = get_language(actual_lang)
        except Exception:
            return [], []

        tree = parser.parse(script_bytes)
        query = Query(ts_lang, scm_text)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)

        tags: list[Tag] = []
        receiver_nodes: dict[int, str] = {}

        for capture_name, nodes in captures.items():
            if capture_name == "method.receiver":
                for node in nodes:
                    line = node.start_point[0] + 1 + line_offset
                    receiver_nodes[line] = node.text.decode("utf-8", errors="replace")
                continue
            if ".definition." in capture_name:
                kind = "def"
            elif ".reference." in capture_name:
                kind = "ref"
            else:
                continue
            for node in nodes:
                name = node.text.decode("utf-8", errors="replace")
                line = node.start_point[0] + 1 + line_offset
                scope = _find_scope(node, tree.root_node)
                node_type = node.parent.type if node.parent else ""
                tags.append(Tag(
                    file=filepath, name=name, line=line,
                    kind=kind, scope=scope, node_type=node_type,
                    capture_name=capture_name,
                ))

        # Add template refs (components + event handlers)
        for ref_name, ref_line in extract_vue_template_refs(filepath=filepath):
            tags.append(Tag(
                file=filepath, name=ref_name, line=ref_line,
                kind="ref", capture_name="name.reference.call",
            ))

        # Build receiver tags
        receiver_tags: list[_ReceiverTag] = []
        for t in tags:
            if t.kind == "ref" and t.line in receiver_nodes:
                receiver_tags.append(_ReceiverTag(
                    file=filepath,
                    receiver_name=receiver_nodes[t.line],
                    method_name=t.name,
                    line=t.line,
                    scope=t.scope,
                ))

        return tags, receiver_tags

    scm_text = _load_query(lang)
    if scm_text is None:
        return [], []

    try:
        parser = get_parser(lang)
        ts_lang = get_language(lang)
    except Exception:
        return [], []

    tree = parser.parse(source)
    query = Query(ts_lang, scm_text)
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    tags: list[Tag] = []
    # Collect receiver nodes keyed by line for pairing
    receiver_nodes: dict[int, str] = {}  # line → receiver_name

    for capture_name, nodes in captures.items():
        if capture_name == "method.receiver":
            for node in nodes:
                line = node.start_point[0] + 1
                receiver_nodes[line] = node.text.decode("utf-8", errors="replace")
            continue

        if ".definition." in capture_name:
            kind = "def"
        elif ".reference." in capture_name:
            kind = "ref"
        else:
            continue

        for node in nodes:
            name = node.text.decode("utf-8", errors="replace")
            line = node.start_point[0] + 1
            scope = _find_scope(node, tree.root_node)
            node_type = node.parent.type if node.parent else ""
            tags.append(Tag(
                file=filepath, name=name, line=line,
                kind=kind, scope=scope, node_type=node_type,
                capture_name=capture_name,
            ))

    # Build ReceiverTags: pair receiver_nodes with @name.reference.call on same line
    receiver_tags: list[_ReceiverTag] = []
    for t in tags:
        if t.kind == "ref" and t.line in receiver_nodes:
            receiver_tags.append(_ReceiverTag(
                file=filepath,
                receiver_name=receiver_nodes[t.line],
                method_name=t.name,
                line=t.line,
                scope=t.scope,
            ))

    return tags, receiver_tags


def _extract_tags(filepath: str, lang: str) -> list[Tag]:
    """Extract definition and reference tags from a file using .scm queries."""
    tags, _ = _extract_tags_and_receivers(filepath, lang)
    return tags


# ---------------------------------------------------------------------------
# Language-specific parsers
# ---------------------------------------------------------------------------


def _parse_vue(filepath: str) -> list[Tag]:
    """Parse a .vue SFC and return Tags."""
    try:
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            return []
        with open(filepath, "rb") as f:
            source = f.read()
    except OSError:
        return []

    try:
        parser = get_parser("vue")
    except Exception:
        return []

    tree = parser.parse(source)
    tags: list[Tag] = []

    for child in tree.root_node.children:
        if child.type == "template_element":
            tags.append(Tag(file=filepath, name="<template>", line=child.start_point[0] + 1, kind="def"))
        elif child.type == "script_element":
            tags.append(Tag(file=filepath, name="<script>", line=child.start_point[0] + 1, kind="def"))
            tags.extend(_parse_vue_script(child, filepath))
        elif child.type == "style_element":
            tags.append(Tag(file=filepath, name="<style>", line=child.start_point[0] + 1, kind="def"))

    return tags


def _parse_vue_script(script_node, filepath: str) -> list[Tag]:
    """Extract Tags from a Vue <script> block using vue_utils + .scm queries."""
    from vue_utils import extract_vue_script

    result = extract_vue_script(filepath=filepath)
    if result is None:
        return []
    script_bytes, lang, line_offset = result

    # Re-use _extract_tags by writing to temp file (existing pattern for _parse_vue display)
    import tempfile
    ext = ".ts" if lang == "typescript" else ".js"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(script_bytes)
        f.flush()
        tmp_path = f.name
    try:
        tags = _extract_tags(tmp_path, lang)
    finally:
        os.unlink(tmp_path)

    for tag in tags:
        tag.file = filepath
        tag.line += line_offset

    return tags


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _should_include(name: str, is_dir: bool) -> bool:
    """Return True if the file/dir should be included in the map."""
    if name.startswith(".env"):
        return not is_dir and name == ".env.example"
    if is_dir:
        return name not in IGNORED_DIRS
    if name in IGNORED_FILES:
        return False
    _, ext = os.path.splitext(name)
    return ext.lower() not in IGNORED_EXTENSIONS


def _ensure_repo_graph_gitignore(root_path: str) -> None:
    """Make generated repo graph caches ignore their own contents."""
    repo_graph_dir = os.path.join(root_path, ".repo-graph")
    if not os.path.isdir(repo_graph_dir):
        return

    gitignore_path = os.path.join(repo_graph_dir, ".gitignore")
    desired = "*\n"
    try:
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                if f.read() == desired:
                    return
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(desired)
    except OSError:
        return


def _parse_file(filepath: str) -> list[Tag]:
    """Parse a file and return Tags, selecting parser by extension."""
    _, ext = os.path.splitext(filepath)
    ext_lower = ext.lower()

    if ext_lower == ".vue":
        return _parse_vue(filepath)

    lang = _EXT_TO_LANG.get(ext_lower)
    if lang:
        return _extract_tags(filepath, lang)

    return []


def _tag_label(tag: Tag, defs: list["Tag"] | None = None) -> str:
    """Return 'name (kind)' using the capture_name suffix, e.g. 'login (function)'.

    Args:
        defs: all def tags in the same file. Used to find the actual enclosing
              scope tag and check if it's a class (→ method) or function (→ function).
    """
    parts = tag.capture_name.rsplit(".", 1)
    kind = parts[-1] if len(parts) > 1 else ""
    # function nested inside a class → method
    if kind == "function" and tag.scope and defs:
        # Find the nearest scope def that: has the right name AND starts before this tag
        scope_tag = None
        for d in defs:
            if d.name == tag.scope and d.line <= tag.line:
                scope_tag = d
        if scope_tag and ".definition.class" in scope_tag.capture_name:
            kind = "method"
    return f"{tag.name} ({kind})" if kind else tag.name


# ---------------------------------------------------------------------------
# RepomapGenerator
# ---------------------------------------------------------------------------


class RepomapGenerator:
    """Generates a lightweight repository map suitable for LLM context."""

    def get_map(self, root_path: str) -> str:
        """Return a tree-like string representation of the project structure.

        The tree includes:
        - Directory hierarchy
        - File names
        - Lightweight code summaries via tree-sitter

        Args:
            root_path: Absolute or relative path to the project root.

        Returns:
            A multi-line string with indented tree structure.
        """
        root_path = os.path.abspath(root_path)
        if not os.path.isdir(root_path):
            return f"Error: '{root_path}' is not a valid directory."
        if not _should_include(os.path.basename(root_path), is_dir=True):
            return "(empty project)"

        _ensure_repo_graph_gitignore(root_path)

        lines: list[str] = []
        all_tags: list[Tag] = []
        self._walk(root_path, lines, all_tags)

        if not lines:
            return "(empty project)"
        if len(lines) > MAX_OUTPUT_LINES:
            lines = lines[:MAX_OUTPUT_LINES]
            lines.append(f"... (truncated at {MAX_OUTPUT_LINES} lines)")
        return "\n".join(lines)

    def _walk(self, current: str, lines: list[str], all_tags: list[Tag],
              prefix: str = "", depth: int = 0) -> None:
        """Recursively walk the directory tree with box-drawing characters."""
        if depth >= MAX_DIR_DEPTH:
            return
        try:
            entries = sorted(os.listdir(current))
        except OSError:
            return

        dirs: list[str] = []
        files: list[str] = []

        for entry in entries:
            full = os.path.join(current, entry)
            if os.path.islink(full):
                continue
            is_dir = os.path.isdir(full)
            if _should_include(entry, is_dir):
                if is_dir:
                    dirs.append(entry)
                else:
                    files.append(entry)

        items: list[tuple[str, bool]] = [(d, True) for d in dirs] + [(f, False) for f in files]
        for i, (name, is_dir) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

            if is_dir:
                lines.append(f"{prefix}{connector}{name}/")
                self._walk(os.path.join(current, name), lines, all_tags,
                           child_prefix, depth + 1)
            else:
                filepath = os.path.join(current, name)
                tags = _parse_file(filepath)
                all_tags.extend(tags)
                defs = sorted([t for t in tags if t.kind == "def"], key=lambda t: t.line)
                lines.append(f"{prefix}{connector}{name}")
                if defs:
                    self._render_tags(defs, lines, child_prefix)

    @staticmethod
    def _render_tags(defs: list[Tag], lines: list[str], prefix: str) -> None:
        """Render tag hierarchy with box-drawing characters.

        Builds a proper tree: each scoped tag is assigned to the nearest
        preceding def whose name matches the scope. Renders recursively
        to support arbitrary nesting depth.
        """
        # Build parent→children mapping using line-based matching
        children: dict[int, list[int]] = {}  # def index → child indices
        roots: list[int] = []

        for i, t in enumerate(defs):
            if not t.scope:
                roots.append(i)
            else:
                # Find nearest preceding def with matching name
                parent = None
                for j in range(i - 1, -1, -1):
                    if defs[j].name == t.scope and defs[j].line <= t.line:
                        parent = j
                        break
                if parent is not None:
                    children.setdefault(parent, []).append(i)
                else:
                    roots.append(i)

        def _render(indices: list[int], pfx: str) -> None:
            for pos, idx in enumerate(indices):
                is_last = pos == len(indices) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{pfx}{connector}{_tag_label(defs[idx], defs)}")
                kids = children.get(idx, [])
                if kids:
                    ext = pfx + ("    " if is_last else "│   ")
                    _render(kids, ext)

        _render(roots, prefix)


# ---------------------------------------------------------------------------
# Singleton & LangChain Tool
# ---------------------------------------------------------------------------
_generator = RepomapGenerator()


@tool
def get_repo_structure(root_path: str | None = None) -> str:
    """Use this tool to get the file structure and code summary of the current
    project to understand context.

    Scans the project directory and returns a tree showing files, classes,
    functions, Vue component sections, and other code-level details.

    Args:
        root_path: Path to project root. Defaults to current working directory.

    Returns:
        A multi-line text tree of the repository structure with code annotations.
    """
    if root_path is None:
        root_path = os.getcwd()
    cwd = os.path.normcase(os.path.realpath(os.getcwd()))
    resolved = os.path.normcase(os.path.realpath(root_path))
    if resolved != cwd and not resolved.startswith(cwd + os.sep):
        return f"Error: path '{root_path}' is outside the project directory."
    return _generator.get_map(resolved)
