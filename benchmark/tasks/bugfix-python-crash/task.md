# Fix crash in user registration

The `POST /users` endpoint crashes with an `AttributeError` when creating a new user.
The server returns a 500 error instead of 201.

## Steps to reproduce
1. Start the server: `uvicorn app.main:app`
2. Send: `POST /users` with body `{"name": "Alice", "email": "alice@example.com"}`
3. Observe 500 error

## Expected behavior
- Returns 201 with `{"id": 1, "name": "Alice", "email": "alice@example.com"}`
- New user is stored in the users list

## Hint
Look at `app/routes/users.py` — there is a typo/attribute error in the user creation logic.
