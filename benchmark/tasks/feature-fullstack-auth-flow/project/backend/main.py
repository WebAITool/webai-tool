from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_items = [{"id": i, "name": f"Item {i}"} for i in range(1, 11)]


@app.get("/api/items")
def list_items():
    return _items