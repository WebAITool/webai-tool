# Fix FastAPI CORS middleware configuration

The FastAPI app in `main.py` has CORS middleware configured incorrectly. The Vue frontend at `http://localhost:5173` cannot make API requests due to CORS errors.

## Bug
- `allow_origins` is set to `["*"]` but the app also sets `allow_credentials=True` — these are incompatible in CORS spec
- `allow_methods` is missing `"PUT"` and `"DELETE"`, so those requests are blocked
- `allow_headers` is missing `"Authorization"`, so JWT auth headers are rejected

## Requirements
1. Change `allow_origins` to `["http://localhost:5173", "http://localhost:3000"]` (specific Vue dev server origins)
2. Set `allow_credentials=False` OR remove it (since specific origins are used, credentials can work, but the combination must be valid)
3. Add `"PUT"` and `"DELETE"` to `allow_methods`
4. Add `"Authorization"` to `allow_headers`
5. Keep all existing routes working
