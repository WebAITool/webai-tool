# Fix Pydantic model validation and schema

The Pydantic schemas in `schemas.py` have several bugs that cause incorrect API behavior.

## Bugs
1. `UserCreate` accepts empty string as `username` — should require min 3 chars
2. `UserCreate.email` has no email validation — `"not-an-email"` passes
3. `ItemCreate.price` accepts negative values — should be `>= 0`
4. `UserResponse` includes `password_hash` in output — should be excluded
5. `ItemResponse.created_at` returns datetime object instead of ISO string — should use `datetime` type with proper serialization

## Requirements
1. Add `min_length=3` to `username` field
2. Add `EmailStr` type for `email` field (from `pydantic`)
3. Add `ge=0` constraint to `price` field
4. Exclude `password_hash` from `UserResponse` (or remove the field entirely)
5. Add `created_at: datetime | None = None` to `ItemResponse` with proper type
6. All existing valid usage must still work
