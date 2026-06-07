from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI()

_items = {1: {"name": "Laptop", "price": 999.99}, 2: {"name": "Mouse", "price": 29.99}}
_next_id = 3


class ItemCreate(BaseModel):
    name: str
    price: float


class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None


@app.get("/items")
def list_items():
    return list(_items.values())


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    return _items[item_id]


@app.post("/items")
def create_item(item: ItemCreate):
    global _next_id
    new_item = {"name": item.name, "price": item.price}
    _items[_next_id] = new_item
    _next_id += 1
    return new_item


@app.put("/items/{item_id}")
def update_item(item_id: int, item: ItemUpdate):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.name is not None:
        _items[item_id]["name"] = item.name
    if item.price is not None:
        _items[item_id]["price"] = item.price
    return _items[item_id]