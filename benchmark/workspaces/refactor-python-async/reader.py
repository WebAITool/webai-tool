import asyncio
import aiofiles
import os
import re
from typing import List, Dict, Optional

class FileReader:
    async def read_file(self, path: str) -> str:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return await f.read()

    async def list_files(self, directory: str) -> List[str]:
        entries = await asyncio.to_thread(os.listdir, directory)
        result = []
        for entry in entries:
            full = os.path.join(directory, entry)
            if await asyncio.to_thread(os.path.isfile, full):
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

    async def search_in_directory(self, directory: str, pattern: str) -> Dict[str, List[int]]:
        files = await self.list_files(directory)
        tasks = [self.search_in_file(f, pattern) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = {}
        for path, lines in zip(files, results):
            if isinstance(lines, list):
                out[path] = lines
            else:
                out[path] = []
        return out
