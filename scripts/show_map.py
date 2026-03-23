"""Show the repository file tree with code annotations."""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if __name__ == "__main__":
    from repo_map import get_repo_structure

    root = sys.argv[1] if len(sys.argv) > 1 else "."
    print(get_repo_structure.invoke({"root_path": root}))
