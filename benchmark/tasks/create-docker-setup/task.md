# Create Docker and Docker Compose configuration

The project has a FastAPI backend and a Vue 3 frontend. Create Docker configuration for the full stack.

## Current project structure
```
backend/
  main.py          # FastAPI app, runs on port 8000
  requirements.txt # Python deps
frontend/
  package.json     # Vue 3 + Vite app, dev server on port 5173
  vite.config.js   # Vite config with proxy /api → http://backend:8000
```

## Requirements

1. **`backend/Dockerfile`**:
   - Base: `python:3.11-slim`
   - Copy requirements.txt, install deps
   - Copy source code
   - Expose port 8000
   - CMD: `uvicorn main:app --host 0.0.0.0 --port 8000`

2. **`frontend/Dockerfile`**:
   - Base: `node:20-alpine`
   - Copy package.json, run `npm install`
   - Copy source code
   - Expose port 5173
   - CMD: `npm run dev -- --host 0.0.0.0`

3. **`docker-compose.yml`** (in project root):
   - `backend` service: build from backend/, port 8000:8000, env vars
   - `frontend` service: build from frontend/, port 5173:5173, depends_on backend
   - `nginx` service: image `nginx:alpine`, port 80:80, depends_on both, volumes for `nginx.conf`
   - Network: `app-network` (bridge)

4. **`nginx.conf`** (in project root):
   - Listen on port 80
   - `/api/` → proxy_pass http://backend:8000
   - `/` → proxy_pass http://frontend:5173
   - WebSocket support for Vite HMR (`Upgrade` headers)

5. **`.dockerignore`** files for both backend/ and frontend/
