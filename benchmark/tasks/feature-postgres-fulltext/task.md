# Add PostgreSQL full-text search with SQLAlchemy

The application has a `Document` model but no search capability. Add PostgreSQL full-text search using `tsvector` and `tsquery` via SQLAlchemy.

## Current code
- `models.py` has a `Document` model with `title`, `content`, and `category` fields
- No search functionality exists

## Requirements

1. Add a `SearchableDocument` model (or extend `Document`) with:
   - `search_vector` column of type `TSVECTOR` (from `sqlalchemy.dialects.postgresql`)
   - A `__table_args__` with a PostgreSQL functional index on `search_vector` using `GIN`

2. Create a database trigger or SQLAlchemy event listener that automatically updates `search_vector` on INSERT or UPDATE by combining `title` (weight A) and `content` (weight B) using `setweight` and `to_tsvector('english', ...)`

3. Implement a search function `search_documents(query_text)` that:
   - Converts the query to a `tsquery` using `plainto_tsquery('english', query_text)`
   - Ranks results using `ts_rank(search_vector, query)`
   - Returns documents ordered by relevance (highest first)
   - Returns the rank as a `relevance` field

4. Ensure the search is case-insensitive and handles English stemming