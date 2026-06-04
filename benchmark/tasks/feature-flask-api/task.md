# Add search and pagination to item API

The existing Flask API has basic CRUD for items. Add search and pagination features.

## Current endpoints
- `GET /items` — returns all items (no filtering, no pagination)
- `POST /items` — create an item
- `GET /items/<id>` — get single item
- `DELETE /items/<id>` — delete an item

## Requirements

1. **Search**: Add `?q=<query>` parameter to `GET /items` that filters items by name (case-insensitive partial match).

2. **Pagination**: Add `?page=<n>&per_page=<m>` parameters to `GET /items`.
   - Default: page=1, per_page=10
   - Response should include: `{"items": [...], "page": 1, "per_page": 10, "total": 42, "pages": 5}`
   - `pages` = ceil(total / per_page)

3. **Search + pagination should work together**: `GET /items?q=apple&page=2&per_page=5`

4. Keep all existing endpoints working exactly as before.
