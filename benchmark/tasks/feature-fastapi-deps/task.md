# Add FastAPI dependency injection for DB sessions

The FastAPI app in `main.py` uses a global in-memory list instead of a database. Refactor it to use SQLAlchemy with proper dependency injection.

## Current state
- `main.py` has CRUD endpoints for items using `_items: list` global
- `database.py` has a `get_db()` generator function stub that returns nothing useful
- `models.py` has an `Item` SQLAlchemy model ready to use

## Requirements

1. Complete `database.py`:
   - Create `engine = create_engine("sqlite:///app.db")`
   - Create `SessionLocal = sessionmaker(bind=engine)`
   - Implement `get_db()` as a generator that yields a session and closes it in `finally`
   - Add `Base.metadata.create_all(engine)` call

2. Update `main.py` routes to use `db: Session = Depends(get_db)`:
   - `GET /items` — query all items from DB
   - `POST /items` — create and add to DB, commit
   - `GET /items/{id}` — query by id, 404 if not found
   - `DELETE /items/{id}` — delete from DB, 404 if not found

3. Remove the global `_items` list and `_next_id` counter

4. Keep the same API contract (same request/response shapes)
