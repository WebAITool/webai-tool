# Add multi-stage Docker builds with production docker-compose

The project has basic Dockerfiles for development. Refactor them to use multi-stage builds for production optimization, and add a production docker-compose.prod.yml.

## Current code
- `backend/Dockerfile` is a single-stage build
- `frontend/Dockerfile` is a single-stage build
- Only `docker-compose.yml` exists (for development)

## Requirements

1. Refactor `backend/Dockerfile` to multi-stage:
   - Stage 1 (builder): install dependencies
   - Stage 2 (runtime): copy only the built artifacts and dependencies, use `python:3.11-slim`
   - Runtime stage should NOT include build tools

2. Refactor `frontend/Dockerfile` to multi-stage:
   - Stage 1 (build): install dependencies and run `npm run build`
   - Stage 2 (production): use `nginx:alpine` to serve the built files
   - Copy the build output to nginx's html directory

3. Create `docker-compose.prod.yml`:
   - Build without volume mounts (use static files/code)
   - Add `nginx` reverse proxy service
   - Set `environment: - ENV=production` on services

4. Keep the original `docker-compose.yml` for development unchanged