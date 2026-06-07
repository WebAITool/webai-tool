# Add JSON/JSONB field with PostgreSQL operators

The SQLAlchemy models currently use basic column types. Add a Product model with a JSONB `metadata` field and implement queries that use PostgreSQL JSON operators.

## Current code
- `models.py` has only a simple `User` model
- No JSON/JSONB types are used

## Requirements

1. Add a `Product` model with fields:
   - `id` (Integer, primary key)
   - `name` (String, not null)
   - `attributes` (JSONB — use `sqlalchemy.dialects.postgresql.JSONB`)
   - `tags` (JSONB — array of strings)
   - `created_at` (DateTime, server_default=func.now())

2. Implement the following query methods:
   - `get_products_by_attribute(key, value)` — uses PostgreSQL `@>` operator to find products where attributes contain the key-value pair
   - `get_products_by_tag(tag)` — uses PostgreSQL `?` operator to find products containing a tag
   - `get_product_attribute(product_id, key)` — returns a specific attribute value from the JSONB field

3. Use `sqlalchemy.dialects.postgresql.JSONB` and `sqlalchemy.dialects.postgresql.JSONB.Comparator` for JSON path queries