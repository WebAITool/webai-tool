# Add full authentication flow with JWT

The FastAPI backend has public endpoints and the Vue frontend has no login page. Add a complete auth flow.

## Current state

- `GET /api/items` — public, returns item list
- Frontend shows items without any authentication

## Requirements

1. **Backend**: Add auth endpoints `POST /api/auth/register` and `POST /api/auth/login`
2. **Backend**: Add `GET /api/auth/me` that returns current user from JWT token
3. **Backend**: Protect `GET /api/items` — require valid `Authorization: Bearer <token>` header
4. **Backend**: Hash passwords with SHA-256, store users in-memory dict
5. **Frontend**: Add login form with username and `<v-text-field>` fields, `<v-btn>` to submit
6. **Frontend**: Store JWT token in `localStorage` after successful login
7. **Frontend**: Attach token to all API requests via `Authorization` header
8. **Frontend**: Detect 401 responses and redirect to login page
9. **Frontend**: Show current username and logout button when authenticated

Use `PyJWT` for tokens, SHA-256 for password hashing, `dev-secret` as default JWT secret with 24h expiry.