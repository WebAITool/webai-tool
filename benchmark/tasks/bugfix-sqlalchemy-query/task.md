# Fix SQLAlchemy query syntax errors

The SQLAlchemy models and queries have several syntax errors. The `models.py` uses `filter()` with incorrect keyword arguments and has a broken comparison in `filter()`.

## Current code
- `models.py` has a User model with basic fields
- Queries use incorrect SQLAlchemy 2.0 syntax

## Requirements

1. Fix the broken query methods in `models.py`:
   - `get_user_by_email()` uses `filter(User.email == email)` — this is correct but the method is missing proper return
   - `get_active_users()` uses `filter(active=True)` — should be `filter(User.active == True)`
   - `search_users()` uses `filter(User.name.contains(query))` — this is correct but method has typo in parameter

2. All tests must pass without errors