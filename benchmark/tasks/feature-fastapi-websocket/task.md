# Add WebSocket endpoint for real-time notifications

The FastAPI app has REST endpoints for items but no real-time communication. Add a WebSocket endpoint that broadcasts notifications when items are created or updated.

## Current code
- `main.py` has CRUD endpoints for items
- No WebSocket support exists

## Requirements

1. Add a WebSocket endpoint at `/ws/notifications` that:
   - Accepts WebSocket connections
   - Maintains a set of active connections
   - Sends a welcome message on connect
   - Broadcasts a JSON message `{"type": "item_created", "item": {...}}` to all connected clients when a new item is POSTed
   - Broadcasts a JSON message `{"type": "item_updated", "item": {...}}` when an item is PUT
   - Handles client disconnects gracefully (removes from active set)

2. Modify the POST `/items` and PUT `/items/{item_id}` endpoints to trigger broadcasts

3. Use `websockets` library (already in requirements) or FastAPI's built-in WebSocket support

4. Keep all existing REST endpoints working