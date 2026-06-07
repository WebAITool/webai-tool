# Add docker-compose with volume mounts for development

The project has a FastAPI backend and a Vue frontend, each with Dockerfiles, but no docker-compose.yml for orchestration. Add docker-compose configuration with volume mounts for hot-reload development.

## Current code
- `backend/Dockerfile` builds the Python FastAPI app
- `frontend/Dockerfile` builds the Vue.js app
- No docker-compose.yml exists

## Requirements

1. Create `docker-compose.yml` with:
   - `backend` service:
     - Build context: `./backend`
     - Port: `8000:8000`
     - Volume mount: `./backend:/app` for hot-reload
     - Command: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
   - `frontend` service:
     - Build context: `./frontend`
     - Port: `5173:5173`
     - Volume mount: `./frontend:/app` for hot-reload
     - Command: `npm run dev -- --host 0.0.0.0`

2. Use named volumes or bind mounts for hot-reload development

3. Both services should be on the same network