"""Data fetcher without caching — every call is expensive."""
import time
from typing import Optional, Dict


# Simulated data sources
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
    def __init__(self, fetch_delay: float = 0.1):
        self.fetch_delay = fetch_delay

    def _simulate_fetch(self):
        """Simulate expensive I/O."""
        time.sleep(self.fetch_delay)

    def fetch_user(self, user_id: int) -> Optional[Dict]:
        self._simulate_fetch()
        return _USERS.get(user_id)

    def fetch_post(self, post_id: int) -> Optional[Dict]:
        self._simulate_fetch()
        return _POSTS.get(post_id)
