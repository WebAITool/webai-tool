# Add pagination for items list on frontend and backend

The FastAPI backend returns all items at once, and the Vue frontend displays them without pagination. Add pagination support on both sides.

## Current code
- `backend/main.py` has a GET `/api/items` that returns all items
- `frontend/src/App.vue` fetches all items and displays them in a list
- No pagination exists

## Requirements

1. Backend: Modify GET `/api/items` to support:
   - `page` query param (default: 1)
   - `per_page` query param (default: 10, max: 100)
   - Return JSON: `{"items": [...], "total": 100, "page": 1, "per_page": 10, "total_pages": 10}`

2. Frontend: Update the Vue component to:
   - Show a paginated list with Previous/Next buttons
   - Display current page info ("Page 1 of 10")
   - Fetch new page data when clicking Previous/Next
   - Disable Previous on first page, Next on last page

3. Use Vite proxy to forward `/api` to backend (or configure CORS)