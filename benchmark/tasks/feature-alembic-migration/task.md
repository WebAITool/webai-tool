# Create Alembic migration for new models

The project has SQLAlchemy models in `models.py` and an Alembic setup in `alembic/`. The initial migration creates the `users` table. Now you need to add a migration for the new `Project` and `Task` models.

## Current state
- `alembic.ini` is configured (sqlite database)
- `alembic/env.py` imports `Base` from `models`
- Initial migration creates `users` table
- `models.py` has `User`, `Project`, and `Task` models defined

## Requirements

1. Create a new Alembic migration (revision) that:
   - Creates `projects` table with columns: id, name, description, owner_id (FK→users.id), status, created_at, updated_at
   - Creates `tasks` table with columns: id, title, description, project_id (FK→projects.id), assignee_id (FK→users.id, nullable), status, priority, created_at, updated_at
   - Foreign keys should have `ondelete="CASCADE"` (except assignee_id which is `SET NULL`)
   - The revision should depend on the initial revision (use `down_revision`)

2. The migration must have both `upgrade()` and `downgrade()` functions
3. Running `alembic upgrade head` should create both tables
4. Running `alembic downgrade -1` should drop both tables
