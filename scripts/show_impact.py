"""Show blast radius for a symbol — what breaks if you change it."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if __name__ == "__main__":
    from graph.builder import build

    if len(sys.argv) < 2:
        print("usage: show_impact.py <name> [direction] [depth] [dir]")
        print("  direction: upstream (default) | downstream")
        sys.exit(1)

    name = sys.argv[1]
    direction = sys.argv[2] if len(sys.argv) > 2 else "upstream"
    max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    root = sys.argv[4] if len(sys.argv) > 4 else "."

    graph = build(root)
    print(graph.impact(name, direction, max_depth))
