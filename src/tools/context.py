# src/tools/context.py
"""LangChain tool wrappers for symbol context queries."""
import os
from langchain_core.tools import tool
from graph.builder import build


@tool
def get_symbol_context(
    name: str,
    file_path: str | None = None,
    root_path: str | None = None,
) -> str:
    """Show full context for a symbol: where defined, who calls it, what it calls.

    Args:
        name: Symbol name (e.g. "login", "UserService")
        file_path: Disambiguate if multiple symbols share the name
        root_path: Project root directory (defaults to current directory)
    """
    root = root_path or os.getcwd()
    graph = build(root)
    return graph.symbol_context(name, file_path)


@tool
def get_symbol_graph(
    symbol: str,
    depth: int = 1,
    root_path: str | None = None,
) -> str:
    """Show the dependency graph for a symbol — what it calls, with configurable depth.

    Args:
        symbol: Symbol name to look up
        depth: BFS depth (default 1)
        root_path: Project root directory (defaults to current directory)
    """
    root = root_path or os.getcwd()
    graph = build(root)
    return graph.symbol_graph(symbol, depth)
