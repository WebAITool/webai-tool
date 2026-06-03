# Fix SQL injection vulnerability

The `UserDB` class in `db.py` uses string formatting to build SQL queries, making it vulnerable to SQL injection attacks.

## Bug
An attacker can bypass authentication by sending `username: "admin' --"` which comments out the password check.

## Requirements
1. Replace all string-formatted SQL with parameterized queries (`?` placeholders)
2. Keep the same public API (`add_user`, `get_user`, `verify_user`, `delete_user`)
3. All existing functionality must still work
4. The injection attack must be prevented
