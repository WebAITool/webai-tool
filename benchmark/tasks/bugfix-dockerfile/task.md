# Fix Dockerfile build errors

The Python backend Dockerfile has several issues that prevent it from building successfully.

## Current code
- `backend/Dockerfile` has errors in the Dockerfile syntax
- `backend/requirements.txt` exists with correct dependencies

## Bugs in Dockerfile
1. `WORKDIR` is misspelled as `WORKDIRR`
2. `COPY` command copies the wrong path (`./app/requirements.txt` instead of `./requirements.txt`)
3. Missing `RUN` before `pip install`
4. The `CMD` instruction uses wrong syntax (`["uvicorn", "main:app"]` should have `--host 0.0.0.0`)

## Requirements
1. Fix all Dockerfile syntax errors
2. Ensure the build succeeds with `docker build -t backend ./backend`
3. The container should start uvicorn on `0.0.0.0:8000`