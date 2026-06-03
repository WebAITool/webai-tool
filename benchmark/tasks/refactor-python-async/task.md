# Refactor sync file reader to async

The `FileReader` class in `reader.py` uses synchronous `open()` / `os.listdir()`. Refactor to use `aiofiles` and `asyncio`.

## Current behavior
- `read_file(path)` — reads entire file (blocking)
- `list_files(directory)` — lists files in directory (blocking)
- `search_in_file(path, pattern)` — searches for text pattern in file (blocking)
- `batch_read(paths)` — reads multiple files sequentially (very slow)

## Requirements

1. **All methods become async** — use `aiofiles` for file I/O, `asyncio` for directory listing
2. **`batch_read` should be concurrent** — use `asyncio.gather()` instead of sequential reads
3. **Add `search_in_directory(directory, pattern)`** — async search across all files in a directory concurrently
4. **Keep same method names** — just add `async` prefix behavior, callers use `await`
5. **Error handling** — missing files should raise `FileNotFoundError`, permission errors should be caught gracefully in batch operations
6. Add `aiofiles` to `requirements.txt`
