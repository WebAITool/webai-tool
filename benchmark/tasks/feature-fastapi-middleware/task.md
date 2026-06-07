# Add request logging and timing middleware

The FastAPI app has endpoints for managing items but no logging or performance monitoring. Add middleware that logs each request with timing information.

## Current code
- `main.py` has CRUD endpoints for items
- No logging or request tracking exists

## Requirements

1. Create `middleware.py` with a middleware function/class that:
   - Logs the HTTP method, path, and status code for every request
   - Measures and logs the request processing time in milliseconds
   - Adds a `X-Process-Time` response header with the elapsed time

2. Use Python's built-in `logging` module (log level INFO)

3. Add a `logging.basicConfig` call in main.py to configure log format

4. Register the middleware in the FastAPI app using `@app.middleware("http")`