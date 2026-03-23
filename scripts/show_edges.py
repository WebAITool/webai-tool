"""Show cross-file reference edges."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if __name__ == "__main__":
    from graph.builder import build

    root = sys.argv[1] if len(sys.argv) > 1 else "."
    graph = build(root)
    print(graph.format_file_edges(root))
