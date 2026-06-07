from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_items = [{"id": i, "name": f"Item {i}", "price": round(i * 10.5, 2)} for i in range(1, 101)]


@app.get("/api/items")
def list_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100)
):
    start = (page - 1) * per_page
    end = start + per_page
    items = _items[start:end]
    total = len(_items)
    total_pages = (total + per_page - 1) // per_page
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }
