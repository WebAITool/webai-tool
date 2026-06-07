# Fix Vite proxy configuration for backend communication

The Vue frontend cannot communicate with the FastAPI backend because the Vite proxy is not configured. API calls to `/api/items` fail with a 404 error.

## Current code
- `vite.config.js` has no proxy configuration
- Frontend calls `fetch('/api/items')` which goes to Vite dev server instead of the backend
- Backend runs on `http://localhost:8000` and has working API endpoints

## Requirements

1. Configure the Vite dev server proxy to forward `/api` requests to `http://localhost:8000`
2. The proxy should rewrite `/api/items` to the backend endpoint
3. Ensure the proxy works with WebSocket connections too (for potential future use)
4. Keep all existing Vite configuration intact