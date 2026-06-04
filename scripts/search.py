"""Search for symbols by name or keyword."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if __name__ == "__main__":
    from graph.builder import build

    if len(sys.argv) < 2:
        print("usage: search.py <query> [kind] [limit] [dir]")
        print("  kind: Function | Class | Method | Interface")
        sys.exit(1)

    query = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    root = sys.argv[4] if len(sys.argv) > 4 else "."

    graph = build(root)
    print(graph.search(query, kind, limit))
