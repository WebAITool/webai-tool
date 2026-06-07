from fastapi import FastAPI, HTTPException

app = FastAPI()

_items = {1: {"name": "Laptop", "price": 999.99}, 2: {"name": "Mouse", "price": 29.99}}
_next_id = 3


@app.get("/items")
def list_items():
    return list(_items.values())


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    return _items[item_id]


@app.post("/items")
def create_item(name: str, price: float):
    global _next_id
    item = {"name": name, "price": price}
    _items[_next_id] = item
    _next_id += 1
    return item