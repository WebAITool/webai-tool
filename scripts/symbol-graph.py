import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from graph.repo_graph import build
name = sys.argv[1] if len(sys.argv) > 1 else ''
depth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
dir = sys.argv[3] if len(sys.argv) > 3 else 'src'
if not name:
    print('usage: symbol-graph <name> [depth] [dir]')
    sys.exit(1)
g = build(dir)
print(g.symbol_graph(name, depth))
