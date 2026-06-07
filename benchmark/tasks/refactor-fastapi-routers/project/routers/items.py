from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ItemCreate(BaseModel):
    name: str
    price: float

_items: list = []
_item_next = 1

@router.get("/items")
def list_items():
    return _items

@router.post("/items", status_code=201)
def create_item(body: ItemCreate):
    global _item_next
    item = {"id": _item_next, "name": body.name, "price": body.price}
    _items.append(item)
    _item_next += 1
    return item

@router.get("/items/{item_id}")
def get_item(item_id: int):
    for i in _items:
        if i["id"] == item_id:
            return i
    raise HTTPException(404, "Item not found")

@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    global _items
    _items = [i for i in _items if i["id"] != item_id]