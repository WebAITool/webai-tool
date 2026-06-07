import asyncio
import aiofiles
import os
import re
from typing import List, Dict, Optional

class FileReader:
    async def read_file(self, path: str) -> str:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return await f.read()

    def list_files(self, directory: str) -> List[str]:
        result = []
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            if os.path.isfile(full):
                result.append(full)
        return result

    async def search_in_file(self, path: str, pattern: str) -> List[int]:
        content = await self.read_file(path)
        lines = content.splitlines()
        return [i + 1 for i, line in enumerate(lines) if re.search(pattern, line)]

    async def batch_read(self, paths: List[str]) -> Dict[str, str]:
        tasks = [self.read_file(path) for path in paths]
        contents = await asyncio.gather(*tasks, return_exceptions=True)
        results = {}
        for path, content in zip(paths, contents):
            if isinstance(content, Exception):
                results[path] = None
            else:
                results[path] = content
        return results
