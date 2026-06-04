"""Show the dependency graph for a symbol."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if __name__ == "__main__":
    from graph.builder import build

    if len(sys.argv) < 2:
        print("usage: show_symbol.py <name> [depth] [dir]")
        sys.exit(1)

    name = sys.argv[1]
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    root = sys.argv[3] if len(sys.argv) > 3 else "."

    graph = build(root)
    print(graph.symbol_graph(name, depth))
