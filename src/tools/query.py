# src/tools/query.py
"""LangChain tool wrapper for symbol keyword search."""
import os
from langchain_core.tools import tool
from graph.builder import build


@tool
def search_symbols(
    query: str,
    kind: str | None = None,
    limit: int = 10,
    root_path: str | None = None,
) -> str:
    """Search for symbols by name or keyword. Returns ranked results.

    Args:
        query: Search query (e.g. "login", "user service")
        kind: Filter by kind — "Function", "Class", "Method", "Interface" (optional)
        limit: Maximum results (default 10)
        root_path: Project root directory (defaults to current directory)
    """
    root = root_path or os.getcwd()
    graph = build(root)
    return graph.search(query, kind, limit)
