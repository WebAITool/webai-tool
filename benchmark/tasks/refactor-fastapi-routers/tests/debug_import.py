import sys
import os
from pathlib import Path

project_dir = Path(__file__).parent.parent / "project"
sys.path.append(str(project_dir))

print(f"PYTHONPATH: {sys.path}")
try:
    import app
    print("Successfully imported app")
except ImportError as e:
    print(f"Failed to import app: {e}")