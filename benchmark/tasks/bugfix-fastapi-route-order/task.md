# Fix route ordering in FastAPI app

The FastAPI app has routes that are incorrectly ordered — a dynamic route `/items/{id}` is defined before a concrete route `/items/stats`, causing the concrete route to never match.

## Bug
- Route `/items/{id}` is defined before `/items/stats`
- When a request to `/items/stats` is made, FastAPI matches `{id}` = "stats" instead of the concrete route
- The `/items/stats` endpoint is unreachable

## Requirements
1. Reorder routes so concrete routes (`/items/stats`) come before dynamic routes (`/items/{id}`)
2. Keep all existing route logic unchanged
3. Verify both `/items/stats` and `/items/{id}` work correctly