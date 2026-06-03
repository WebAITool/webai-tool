"""Tests for feature-python-caching task."""
import time
import threading
import pytest
from fetcher import DataFetcher


@pytest.fixture
def fetcher():
    return DataFetcher(fetch_delay=0.05)


def test_fetch_user_returns_data(fetcher):
    user = fetcher.fetch_user(1)
    assert user is not None
    assert user["name"] == "Alice"


def test_fetch_post_returns_data(fetcher):
    post = fetcher.fetch_post(1)
    assert post is not None
    assert post["title"] == "Hello"


def test_cache_speeds_up_second_call(fetcher):
    fetcher.fetch_user(1)  # First call: slow
    start = time.time()
    fetcher.fetch_user(1)  # Second call: should be cached
    elapsed = time.time() - start
    assert elapsed < 0.03, f"Second call took {elapsed:.3f}s — cache not working"


def test_cache_stats_exist(fetcher):
    stats = fetcher.cache_stats()
    assert isinstance(stats, dict)
    assert "hits" in stats
    assert "misses" in stats
    assert "size" in stats


def test_cache_stats_tracking(fetcher):
    fetcher.fetch_user(1)   # miss
    fetcher.fetch_user(1)   # hit
    fetcher.fetch_user(2)   # miss
    stats = fetcher.cache_stats()
    assert stats["hits"] >= 1
    assert stats["misses"] >= 2


def test_invalidate_specific_key(fetcher):
    fetcher.fetch_user(1)
    fetcher.invalidate(key=("fetch_user", 1))
    # Should be a miss now
    start = time.time()
    fetcher.fetch_user(1)
    elapsed = time.time() - start
    assert elapsed >= 0.03, "Invalidation didn't work — still cached"


def test_invalidate_all(fetcher):
    fetcher.fetch_user(1)
    fetcher.fetch_user(2)
    fetcher.invalidate()
    stats = fetcher.cache_stats()
    assert stats["size"] == 0


def test_ttl_expiry(fetcher):
    fetcher_ttl = DataFetcher(fetch_delay=0.01)
    # Manually set short TTL if supported
    if hasattr(fetcher_ttl, 'ttl_seconds'):
        fetcher_ttl.ttl_seconds = 0.05
    fetcher_ttl.fetch_user(1)
    time.sleep(0.1)  # Wait for TTL to expire
    start = time.time()
    fetcher_ttl.fetch_user(1)
    elapsed = time.time() - start
    # After TTL, should be a miss (slow again)
    # If TTL not configurable, this test passes trivially
    if hasattr(fetcher_ttl, 'ttl_seconds'):
        assert elapsed >= 0.005, "TTL didn't expire"
