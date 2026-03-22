import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from repo_map import get_repo_structure
print(get_repo_structure.invoke({'root_path': sys.argv[1] if len(sys.argv) > 1 else '.'}))
