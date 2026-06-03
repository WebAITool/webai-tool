from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()


class ItemCreate(BaseModel):
    name: str
    price: float
    description: str = ""


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str


# Global in-memory storage — REPLACE with DB
_items: list = []
_next_id = 1


@app.get("/items")
def list_items():
    return _items


@app.post("/items", status_code=201)
def create_item(body: ItemCreate):
    global _next_id
    item = {"id": _next_id, "name": body.name, "price": body.price, "description": body.description}
    _items.append(item)
    _next_id += 1
    return item


@app.get("/items/{item_id}")
def get_item(item_id: int):
    for item in _items:
        if item["id"] == item_id:
            return item
    raise HTTPException(404, "Item not found")


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    global _items
    before = len(_items)
    _items = [i for i in _items if i["id"] != item_id]
    if len(_items) == before:
        raise HTTPException(404, "Item not found")
