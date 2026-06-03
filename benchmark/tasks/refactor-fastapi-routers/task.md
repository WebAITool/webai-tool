# Split monolithic FastAPI app into routers

The `main.py` file has all routes in a single file — users, items, and health check. Refactor into separate router modules.

## Current structure (all in main.py)
- Health check routes: `GET /health`, `GET /`
- User routes: `GET /users`, `POST /users`, `GET /users/{id}`, `DELETE /users/{id}`
- Item routes: `GET /items`, `POST /items`, `GET /items/{id}`, `DELETE /items/{id}`

## Target structure
```
app/
  __init__.py          # creates FastAPI app, includes routers
  routers/
    __init__.py
    health.py          # GET /health, GET /
    users.py           # all /users routes
    items.py           # all /items routes
  main.py              # entry point: from app import app; uvicorn.run
```

## Requirements
1. Create `app/` package with `__init__.py` that creates the FastAPI instance
2. Create `app/routers/` package with `health.py`, `users.py`, `items.py`
3. Each router uses `APIRouter()` with appropriate `prefix` and `tags`
4. `app/__init__.py` includes all routers with `app.include_router()`
5. `main.py` at project root becomes just `from app import app` + uvicorn run
6. All existing API endpoints must work identically (same URLs, same responses)
7. CORS middleware stays in `app/__init__.py`
