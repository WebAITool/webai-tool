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
def list_items():
    return _items