"""FastAPI app with broken CORS configuration."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# BUG: CORS misconfigured
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # BUG: incompatible with allow_credentials=True
    allow_credentials=True,       # BUG: can't use True with "*"
    allow_methods=["GET", "POST"],  # BUG: missing PUT, DELETE
    allow_headers=["Content-Type"],  # BUG: missing Authorization
)


class ItemCreate(BaseModel):
    name: str
    price: float


_items: list = []
_next_id = 1


@app.get("/items")
def list_items():
    return _items


@app.post("/items", status_code=201)
def create_item(body: ItemCreate):
    global _next_id
    item = {"id": _next_id, "name": body.name, "price": body.price}
    _items.append(item)
    _next_id += 1
    return item


@app.put("/items/{item_id}")
def update_item(item_id: int, body: ItemCreate):
    for item in _items:
        if item["id"] == item_id:
            item["name"] = body.name
            item["price"] = body.price
            return item
    return {"error": "not found"}


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    global _items
    _items = [i for i in _items if i["id"] != item_id]
