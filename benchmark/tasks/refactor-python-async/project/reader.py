"""Synchronous file reader — needs async refactor."""
import os
import re
from typing import List, Dict, Optional


class FileReader:
    def read_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def list_files(self, directory: str) -> List[str]:
        result = []
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            if os.path.isfile(full):
                result.append(full)
        return result

    def search_in_file(self, path: str, pattern: str) -> List[int]:
        """Return line numbers where pattern matches."""
        content = self.read_file(path)
        lines = content.splitlines()
        return [i + 1 for i, line in enumerate(lines) if re.search(pattern, line)]

    def batch_read(self, paths: List[str]) -> Dict[str, str]:
        """Read multiple files sequentially — SLOW."""
        results = {}
        for path in paths:
            try:
                results[path] = self.read_file(path)
            except FileNotFoundError:
                results[path] = None
        return results
