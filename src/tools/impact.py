# src/tools/impact.py
"""LangChain tool wrapper for blast radius analysis."""
import os
from langchain_core.tools import tool
from graph.builder import build


@tool
def get_impact(
    target: str,
    direction: str = "upstream",
    max_depth: int = 3,
    min_confidence: float = 0.7,
    file_path: str | None = None,
    root_path: str | None = None,
) -> str:
    """Analyze what breaks if you change a symbol.

    Args:
        target: Symbol name to analyze
        direction: "upstream" (who depends on this) or "downstream" (what this depends on)
        max_depth: BFS depth limit (default 3)
        min_confidence: Minimum edge confidence to follow (default 0.7)
        file_path: Disambiguate if multiple symbols share the name
        root_path: Project root directory (defaults to current directory)
    """
    root = root_path or os.getcwd()
    graph = build(root)
    return graph.impact(target, direction, max_depth, min_confidence, file_path)
