"""Data fetcher with in-memory caching layer."""
import time
import threading
from typing import Optional, Dict, Tuple, Any

_USERS = {
    1: {"id": 1, "name": "Alice", "email": "alice@test.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@test.com"},
    3: {"id": 3, "name": "Carol", "email": "carol@test.com"},
}

_POSTS = {
    1: {"id": 1, "title": "Hello", "author_id": 1},
    2: {"id": 2, "title": "World", "author_id": 2},
}

class DataFetcher:
    def __init__(self, fetch_delay: float = 0.1, ttl_seconds: int = 60):
        self.fetch_delay = fetch_delay
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[Tuple[str, int], Any] = {}
        self._timestamps: Dict[Tuple[str, int], float] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _simulate_fetch(self):
        time.sleep(self.fetch_delay)

    def _get_from_cache(self, key: Tuple[str, int]):
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self.ttl_seconds:
                    self._hits += 1
                    return self._cache[key]
                else:
                    del self._cache[key]
                    del self._timestamps[key]
            self._misses += 1
            return None

    def _set_cache(self, key: Tuple[str, int], value: Any):
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def fetch_user(self, user_id: int) -> Optional[Dict]:
        key = ("fetch_user", user_id)
        cached = self._get_from_cache(key)
        if cached is not None:
            return cached
        self._simulate_fetch()
        result = _USERS.get(user_id)
        self._set_cache(key, result)
        return result

    def fetch_post(self, post_id: int) -> Optional[Dict]:
        key = ("fetch_post", post_id)
        cached = self._get_from_cache(key)
        if cached is not None:
            return cached
        self._simulate_fetch()
        result = _POSTS.get(post_id)
        self._set_cache(key, result)
        return result

    def invalidate(self, key: Optional[Tuple[str, int]] = None):
        with self._lock:
            if key is None:
                self._cache.clear()
                self._timestamps.clear()
            else:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)

    def cache_stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache)
            }
