# Add JWT authentication to FastAPI app

The existing FastAPI app has public endpoints for managing notes. Add JWT-based authentication.

## Current endpoints (all public)
- `GET /notes` — list all notes
- `POST /notes` — create a note (body: `{title, content}`)
- `GET /notes/{id}` — get single note
- `DELETE /notes/{id}` — delete a note

## Requirements

1. **User registration**: `POST /auth/register` — body: `{username, password}`, returns `{id, username, token}`
2. **User login**: `POST /auth/login` — body: `{username, password}`, returns `{token}`
3. **JWT middleware**: All `/notes` endpoints now require `Authorization: Bearer <token>` header
4. **Notes are per-user**: Each note belongs to a user. `GET /notes` returns only the current user's notes.
5. **Token format**: Use `PyJWT` with HS256, expiry 24h, secret from env var `JWT_SECRET` (default: "dev-secret")
6. **Error responses**: 401 for missing/invalid token, 403 for wrong user

Keep the existing code structure. Add `auth.py` module for auth logic.
