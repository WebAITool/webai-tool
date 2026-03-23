"""Show git changes mapped to affected symbols and their callers."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if __name__ == "__main__":
    from tools.changes import detect_changes

    scope = sys.argv[1] if len(sys.argv) > 1 else "unstaged"
    root = sys.argv[2] if len(sys.argv) > 2 else "."

    print(detect_changes.invoke({"scope": scope, "root_path": root}))
