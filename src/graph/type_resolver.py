# src/graph/type_resolver.py
"""Lightweight type binding extraction from AST for method call resolution."""
from __future__ import annotations

from graph.models import TypeBinding


def extract_type_bindings(filepath: str, lang: str) -> list[TypeBinding]:
    """Extract variable-to-type bindings from 4 static AST patterns."""
    from tree_sitter import Query, QueryCursor
    from tree_sitter_language_pack import get_language, get_parser

    query_specs = _BINDING_QUERIES.get(lang)
    if query_specs is None:
        return []

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

    # Each query spec is (scm_text, source_tag) so we know which pattern matched
    vars_: dict[int, str] = {}    # line → var_name
    types_: dict[int, str] = {}   # line → type_name
    sources_: dict[int, str] = {} # line → source tag

    for scm_text, source_tag in query_specs:
        try:
            query = Query(ts_lang, scm_text)
        except Exception:
            continue
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)

        for cap_name, nodes in captures.items():
            for node in nodes:
                line = node.start_point[0] + 1
                text = node.text.decode("utf-8", errors="replace")
                if cap_name == "binding.var":
                    vars_[line] = text
                elif cap_name == "binding.type":
                    # Only accept PascalCase type names (filters out lowercase function calls)
                    if text and text[0].isupper():
                        types_[line] = text
                        sources_[line] = source_tag

    bindings: list[TypeBinding] = []
    for line, var in vars_.items():
        # Find type on same or adjacent line (within 2 lines for multiline declarations)
        type_name = None
        source_tag = "annotation"
        for delta in range(3):
            if (line + delta) in types_:
                type_name = types_[line + delta]
                source_tag = sources_.get(line + delta, "annotation")
                break
            if delta > 0 and (line - delta) in types_:
                type_name = types_[line - delta]
                source_tag = sources_.get(line - delta, "annotation")
                break
        if type_name:
            scope = _find_scope_at_line(tree, line)
            bindings.append(TypeBinding(
                file=filepath,
                var_name=var,
                resolved_type=type_name,
                scope=scope,
                source=source_tag,
            ))

    return bindings


def _find_scope_at_line(tree, line: int) -> str:
    """Find enclosing function/method name for a given line number."""
    scope_types = {
        "function_definition", "class_definition",
        "function_declaration", "class_declaration",
        "method_definition", "arrow_function",
    }

    def _walk(node):
        if node.start_point[0] + 1 <= line <= node.end_point[0] + 1:
            if node.type in scope_types:
                name_node = node.child_by_field_name("name")
                if name_node:
                    child_scope = None
                    for child in node.children:
                        child_scope = _walk(child)
                        if child_scope:
                            return child_scope
                    return name_node.text.decode("utf-8", errors="replace")
            for child in node.children:
                result = _walk(child)
                if result:
                    return result
        return None

    return _walk(tree.root_node) or ""


# --- Language-specific binding queries ---
# Each entry is a list of (scm_text, source_tag) tuples.

_PYTHON_BINDINGS: list[tuple[str, str]] = [
    # var = ClassName()
    ("""
(assignment
  left: (identifier) @binding.var
  right: (call function: (identifier) @binding.type))
""", "constructor"),
    # def func(param: ClassName)
    ("""
(typed_parameter
  (identifier) @binding.var
  type: (type (identifier) @binding.type))
""", "annotation"),
]

_TS_BINDINGS: list[tuple[str, str]] = [
    # const s = new UserService()
    ("""
(variable_declarator
  name: (identifier) @binding.var
  value: (new_expression (identifier) @binding.type))
""", "new_expression"),
    # const s: UserService = ...
    ("""
(variable_declarator
  name: (identifier) @binding.var
  type: (type_annotation (type_identifier) @binding.type))
""", "annotation"),
    # function handle(s: UserService)
    ("""
(required_parameter
  name: (identifier) @binding.var
  type: (type_annotation (type_identifier) @binding.type))
""", "annotation"),
]

_BINDING_QUERIES: dict[str, list[tuple[str, str]]] = {
    "python": _PYTHON_BINDINGS,
    "typescript": _TS_BINDINGS,
    "tsx": _TS_BINDINGS,
}
