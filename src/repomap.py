"""
repomap.py — Repository Map Generator for WebAI Toolkit.

Generates a tree-like map of a project's file structure with code
analysis (classes, functions, methods, etc.) powered by tree-sitter.
Supports Python, JavaScript, TypeScript, and Vue out of the box.
"""

import os

from langchain_core.tools import tool
from tree_sitter_language_pack import SupportedLanguage, get_parser


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 512 * 1024  # 512 KB — skip files larger than this
MAX_DIR_DEPTH = 30  # max directory nesting depth to prevent infinite recursion
MAX_AST_DEPTH = 20  # max AST nesting depth for class/function extraction
MAX_OUTPUT_LINES = 5000  # truncate output to prevent context window overflow

IGNORED_DIRS = {
    ".git",
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
}


# ---------------------------------------------------------------------------
# Per-language node type queries
# ---------------------------------------------------------------------------

_NODE_CONFIG: dict[str, dict] = {
    "python": {
        "class_types": {"class_definition"},
        "function_types": {"function_definition"},
        "name_field": "name",
    },
    "javascript": {
        "class_types": {"class_declaration"},
        "function_types": {"function_declaration"},
        "method_types": {"method_definition"},
        "name_field": "name",
        "arrow_var": True,
    },
    "typescript": {
        "class_types": {"class_declaration", "abstract_class_declaration"},
        "function_types": {"function_declaration"},
        "method_types": {"method_definition"},
        "name_field": "name",
        "arrow_var": True,
    },
    "tsx": {
        "class_types": {"class_declaration"},
        "function_types": {"function_declaration"},
        "method_types": {"method_definition"},
        "name_field": "name",
        "arrow_var": True,
    },
}

# Fallback config for languages added to _EXT_TO_LANG without a _NODE_CONFIG entry.
# Currently unreachable but kept as a safety net for future language additions.
_DEFAULT_CONFIG = {
    "class_types": {"class_definition", "class_declaration"},
    "function_types": {"function_definition", "function_declaration"},
    "method_types": {"method_definition", "method_declaration"},
    "name_field": "name",
}


# ---------------------------------------------------------------------------
# Tree-sitter parsing helpers
# ---------------------------------------------------------------------------


def _get_node_name(node, name_field: str | None) -> str:
    """Extract the name from a tree-sitter node."""
    if name_field is None:
        for child in node.children:
            if child.type in (
                "identifier",
                "simple_identifier",
                "property_identifier",
                "type_identifier",
            ):
                return child.text.decode("utf-8", errors="replace")
        return "?"

    name_node = node.child_by_field_name(name_field)
    if name_node:
        return name_node.text.decode("utf-8", errors="replace")

    for child in node.children:
        if child.type in (
            "identifier",
            "simple_identifier",
            "property_identifier",
            "type_identifier",
        ):
            return child.text.decode("utf-8", errors="replace")
    return "?"


def _get_params(node) -> str:
    """Extract function parameters text if available (single-line)."""
    params_node = node.child_by_field_name("parameters")
    if not params_node:
        for child in node.children:
            if child.type in ("parameters", "formal_parameters"):
                params_node = child
                break
    if params_node:
        raw = params_node.text.decode("utf-8", errors="replace")
        return " ".join(raw.split())
    return ""


def _extract_items(node, config: dict, depth: int = 0) -> list[str]:
    """Recursively extract classes, functions, methods from tree-sitter AST."""
    if depth >= MAX_AST_DEPTH:
        return []
    items: list[str] = []
    class_types = config.get("class_types", set())
    func_types = config.get("function_types", set())
    method_types = config.get("method_types", set())
    name_field = config.get("name_field", "name")
    has_arrow_var = config.get("arrow_var", False)

    for child in node.children:
        ntype = child.type

        if ntype in class_types:
            name = _get_node_name(child, name_field)
            prefix = "  " * depth
            items.append(f"{prefix}class {name}")
            for sub in child.children:
                if sub.type in (
                    "block",
                    "class_body",
                    "body",
                    "declaration_list",
                    "enum_body",
                ):
                    items.extend(_extract_items(sub, config, depth + 1))

        elif ntype in func_types or ntype in method_types:
            name = _get_node_name(child, name_field)
            params = _get_params(child)
            prefix = "  " * depth
            items.append(
                f"{prefix}def {name}{params}" if params else f"{prefix}def {name}()"
            )

        elif ntype in ("decorated_definition", "export_statement"):
            items.extend(_extract_items(child, config, depth))

        elif has_arrow_var and ntype == "lexical_declaration":
            for decl in child.children:
                if decl.type == "variable_declarator":
                    value = decl.child_by_field_name("value")
                    if value and value.type == "arrow_function":
                        vname = decl.child_by_field_name("name")
                        if vname:
                            arrow_name = vname.text.decode("utf-8", errors="replace")
                            params = _get_params(value)
                            prefix = "  " * depth
                            items.append(
                                f"{prefix}const {arrow_name} = {params} =>"
                                if params
                                else f"{prefix}const {arrow_name} = () =>"
                            )

    return items


# ---------------------------------------------------------------------------
# Language-specific parsers
# ---------------------------------------------------------------------------


def _parse_with_treesitter(filepath: str, lang: SupportedLanguage) -> list[str]:
    """Parse a file using tree-sitter and extract code structure items."""
    try:
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            return []
        with open(filepath, "rb") as f:
            source = f.read()
    except OSError:
        return []

    try:
        parser = get_parser(lang)
    except Exception:
        return []

    tree = parser.parse(source)
    config = _NODE_CONFIG.get(lang, _DEFAULT_CONFIG)
    return _extract_items(tree.root_node, config)


def _parse_vue(filepath: str) -> list[str]:
    """Parse a .vue file: extract sections and parse <script> with JS parser."""
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
    items: list[str] = []

    for child in tree.root_node.children:
        if child.type == "template_element":
            items.append("<template>")
        elif child.type == "script_element":
            items.append("<script>")
            script_items = _parse_vue_script(child)
            items.extend(f"  {si}" for si in script_items)
        elif child.type == "style_element":
            items.append("<style>")

    return items


def _parse_vue_script(script_node) -> list[str]:
    """Extract function/class info from a Vue <script> block."""
    lang = "javascript"
    start_tag = None
    for child in script_node.children:
        if child.type == "start_tag":
            start_tag = child
            break
    if start_tag:
        for attr in start_tag.children:
            if attr.type == "attribute":
                attr_name = None
                attr_value = None
                for ac in attr.children:
                    if ac.type == "attribute_name":
                        attr_name = ac.text.decode("utf-8", errors="replace")
                    elif ac.type == "quoted_attribute_value":
                        attr_value = ac.text.decode("utf-8", errors="replace").strip(
                            "\"'"
                        )
                if attr_name == "lang" and attr_value in ("ts", "typescript"):
                    lang = "typescript"

    raw_text = None
    for child in script_node.children:
        if child.type == "raw_text":
            raw_text = child
            break

    if not raw_text:
        return []

    script_source = raw_text.text
    try:
        js_parser = get_parser(lang)
    except Exception:
        return []

    js_tree = js_parser.parse(script_source)
    config = _NODE_CONFIG.get(lang, _DEFAULT_CONFIG)

    # Composition API (function declarations, arrow functions)
    extracted = _extract_items(js_tree.root_node, config)

    # Vue Options API (methods: { ... }, computed: { ... })
    vue_methods = _extract_vue_options_methods(js_tree.root_node)
    extracted.extend(vue_methods)

    return extracted


def _extract_vue_options_methods(node) -> list[str]:
    """Extract method names from Vue Options API patterns."""
    items: list[str] = []
    _find_vue_methods_recursive(node, items)
    return items


def _find_vue_methods_recursive(node, items: list[str], depth: int = 0) -> None:
    """Recursively search for Vue Options API method definitions."""
    if depth >= MAX_AST_DEPTH:
        return
    if node.type == "pair":
        key = node.child_by_field_name("key")
        value = node.child_by_field_name("value")
        if key and value:
            key_text = key.text.decode("utf-8", errors="replace")
            if key_text in ("methods", "computed", "watch") and value.type == "object":
                for prop in value.children:
                    if prop.type == "pair":
                        pkey = prop.child_by_field_name("key")
                        if pkey:
                            name = pkey.text.decode("utf-8", errors="replace")
                            items.append(f"def {name}()")
                    elif prop.type == "method_definition":
                        for ch in prop.children:
                            if ch.type == "property_identifier":
                                name = ch.text.decode("utf-8", errors="replace")
                                items.append(f"def {name}()")
                                break
                return

    for child in node.children:
        _find_vue_methods_recursive(child, items, depth + 1)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _should_include(name: str, is_dir: bool) -> bool:
    """Return True if the file/dir should be included in the map."""
    if is_dir:
        return name not in IGNORED_DIRS
    if name in IGNORED_FILES:
        return False
    _, ext = os.path.splitext(name)
    return ext.lower() not in IGNORED_EXTENSIONS


def _parse_file(filepath: str) -> list[str]:
    """Parse a file and return structure items, selecting parser by extension."""
    _, ext = os.path.splitext(filepath)
    ext_lower = ext.lower()

    if ext_lower == ".vue":
        return _parse_vue(filepath)

    lang = _EXT_TO_LANG.get(ext_lower)
    if lang:
        return _parse_with_treesitter(filepath, lang)

    return []


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

        lines: list[str] = []
        self._walk(root_path, lines, indent=0)
        if not lines:
            return "(empty project)"
        if len(lines) > MAX_OUTPUT_LINES:
            lines = lines[:MAX_OUTPUT_LINES]
            lines.append(f"... (truncated at {MAX_OUTPUT_LINES} lines)")
        return "\n".join(lines)

    def _walk(self, current: str, lines: list[str], indent: int) -> None:
        """Recursively walk the directory tree."""
        if indent >= MAX_DIR_DEPTH:
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

        prefix = "  " * indent

        for d in dirs:
            lines.append(f"{prefix}{d}/")
            self._walk(os.path.join(current, d), lines, indent + 1)

        for fname in files:
            lines.append(f"{prefix}{fname}")
            filepath = os.path.join(current, fname)
            details = _parse_file(filepath)
            for detail in details:
                stripped = detail.lstrip(' ')
                inner_spaces = len(detail) - len(stripped)
                lines.append(f"{prefix}{'  ' * (inner_spaces // 2 + 1)}L {stripped}")


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
    # Prevent path traversal — resolve to absolute and ensure it stays
    # within the current working directory.  normcase handles
    # case-insensitive filesystems (Windows NTFS).
    cwd = os.path.normcase(os.path.realpath(os.getcwd()))
    resolved = os.path.normcase(os.path.realpath(root_path))
    if resolved != cwd and not resolved.startswith(cwd + os.sep):
        return f"Error: path '{root_path}' is outside the project directory."
    return _generator.get_map(resolved)
