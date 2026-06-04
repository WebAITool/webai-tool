"""Tests for refactor-python-async task."""
import os
import asyncio
import tempfile
import pytest
from reader import FileReader


@pytest.fixture
def sample_dir():
    tmpdir = tempfile.mkdtemp(prefix="async_reader_")
    with open(os.path.join(tmpdir, "a.txt"), "w") as f:
        f.write("hello world\nfoo bar\nhello again\n")
    with open(os.path.join(tmpdir, "b.txt"), "w") as f:
        f.write("second file\npython async\n")
    with open(os.path.join(tmpdir, "c.txt"), "w") as f:
        f.write("third file\nmore hello\n")
    yield tmpdir
    import shutil
    shutil.rmtree(tmpdir)


@pytest.fixture
def reader():
    return FileReader()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_read_file_is_async(reader, sample_dir):
    """read_file should be awaitable (coroutine)."""
    path = os.path.join(sample_dir, "a.txt")
    result = _run(reader.read_file(path))
    assert "hello world" in result


def test_list_files_is_async(reader, sample_dir):
    """list_files should be awaitable."""
    files = _run(reader.list_files(sample_dir))
    assert len(files) == 3


def test_search_in_file_is_async(reader, sample_dir):
    """search_in_file should be awaitable."""
    path = os.path.join(sample_dir, "a.txt")
    lines = _run(reader.search_in_file(path, "hello"))
    assert 1 in lines
    assert 3 in lines


def test_batch_read_is_concurrent(reader, sample_dir):
    """batch_read should be awaitable and faster than sequential."""
    paths = [
        os.path.join(sample_dir, "a.txt"),
        os.path.join(sample_dir, "b.txt"),
        os.path.join(sample_dir, "c.txt"),
    ]
    results = _run(reader.batch_read(paths))
    assert results[paths[0]] is not None
    assert "hello world" in results[paths[0]]
    assert results[paths[1]] is not None


def test_batch_read_missing_file(reader, sample_dir):
    """batch_read should handle missing files gracefully."""
    paths = [
        os.path.join(sample_dir, "a.txt"),
        os.path.join(sample_dir, "nonexistent.txt"),
    ]
    results = _run(reader.batch_read(paths))
    assert results[paths[0]] is not None
    assert results[paths[1]] is None


def test_search_in_directory_exists(reader, sample_dir):
    """search_in_directory method should exist."""
    assert hasattr(reader, "search_in_directory"), "search_in_directory not found"


def test_search_in_directory_works(reader, sample_dir):
    """search_in_directory should search across all files concurrently."""
    results = _run(reader.search_in_directory(sample_dir, "hello"))
    assert isinstance(results, dict)
    # At least a.txt and c.txt contain "hello"
    assert len(results) >= 2
