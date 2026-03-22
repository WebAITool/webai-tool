import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from graph.repo_graph import build
dir = sys.argv[1] if len(sys.argv) > 1 else 'src'
g = build(dir)
print(g.format_file_edges(dir))
