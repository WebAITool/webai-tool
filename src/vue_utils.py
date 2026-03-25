# src/vue_utils.py
"""Vue SFC helpers — script extraction and template ref parsing.

Neutral module: no imports from repo_map or graph.* to avoid circular deps.
"""
from __future__ import annotations


def extract_vue_script(
    filepath: str | None = None, source: bytes | None = None
) -> tuple[bytes, str, int] | None:
    """Parse .vue with tree-sitter-vue, extract <script> or <script setup>.

    Args:
        filepath: Path to .vue file (reads from disk).
        source: Raw .vue bytes (used instead of filepath if provided).

    Returns:
        (script_bytes, lang, line_offset) or None if no script block.
        lang is "javascript" or "typescript".
        line_offset is the 0-indexed line where the script content starts.
    """
    from tree_sitter_language_pack import get_parser

    if source is None:
        if filepath is None:
            return None
        try:
            with open(filepath, "rb") as f:
                source = f.read()
        except OSError:
            return None

    try:
        parser = get_parser("vue")
    except Exception:
        return None

    tree = parser.parse(source)

    for child in tree.root_node.children:
        if child.type != "script_element":
            continue

        # Detect lang from <script lang="ts">
        lang = "javascript"
        for tag_child in child.children:
            if tag_child.type == "start_tag":
                for attr in tag_child.children:
                    if attr.type == "attribute":
                        attr_name = None
                        attr_value = None
                        for ac in attr.children:
                            if ac.type == "attribute_name":
                                attr_name = ac.text.decode("utf-8", errors="replace")
                            elif ac.type == "quoted_attribute_value":
                                attr_value = ac.text.decode(
                                    "utf-8", errors="replace"
                                ).strip("\"'")
                        if attr_name == "lang" and attr_value in ("ts", "typescript"):
                            lang = "typescript"
                break

        # Extract raw_text content
        for sub in child.children:
            if sub.type == "raw_text":
                return (sub.text, lang, sub.start_point[0])

    return None


def extract_vue_template_refs(
    filepath: str | None = None, source: bytes | None = None
) -> list[tuple[str, int]]:
    """Extract component usage and event handler refs from <template>.

    Returns list of (name, line) tuples.
    """
    from tree_sitter_language_pack import get_parser

    if source is None:
        if filepath is None:
            return []
        try:
            with open(filepath, "rb") as f:
                source = f.read()
        except OSError:
            return []

    try:
        parser = get_parser("vue")
    except Exception:
        return []

    tree = parser.parse(source)
    refs: list[tuple[str, int]] = []

    def _walk(node):
        # Component usage: PascalCase tag names
        if node.type in ("self_closing_tag", "start_tag"):
            for child in node.children:
                if child.type == "tag_name":
                    name = child.text.decode("utf-8", errors="replace")
                    if name and name[0].isupper():
                        refs.append((name, child.start_point[0] + 1))
                    break

        # Event handlers: @click="methodName"
        if node.type == "directive_attribute":
            has_at = False
            for child in node.children:
                if child.type == "@":
                    has_at = True
                elif has_at and child.type == "quoted_attribute_value":
                    for val in child.children:
                        if val.type == "attribute_value":
                            name = val.text.decode("utf-8", errors="replace")
                            if name and name.isidentifier():
                                refs.append((name, val.start_point[0] + 1))
                    break

        for child in node.children:
            _walk(child)

    _walk(tree.root_node)
    return refs
