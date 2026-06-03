# Add caching layer to data fetcher

The `DataFetcher` class in `fetcher.py` makes expensive calls (simulated with `time.sleep`). Add an in-memory caching layer.

## Current behavior
- `fetch_user(user_id)` — always "fetches" from source (sleeps 0.1s)
- `fetch_post(post_id)` — always "fetches" from source (sleeps 0.1s)
- No caching at all

## Requirements

1. **In-memory cache**: Results are cached in a dict keyed by (method, id)
2. **TTL support**: Cache entries expire after `ttl_seconds` (default: 60)
3. **Cache invalidation**: `invalidate(key=None)` — if key given, remove one entry; if None, clear all
4. **Cache stats**: `cache_stats()` returns `{"hits": N, "misses": N, "size": N}`
5. **Thread-safe**: Use `threading.Lock` for the cache dict
6. Keep all existing methods working, just add caching transparently
