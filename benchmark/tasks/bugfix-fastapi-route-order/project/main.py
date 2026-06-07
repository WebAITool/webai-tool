from fastapi import FastAPI, HTTPException

app = FastAPI()

_items = {1: {"name": "Laptop", "price": 999.99}, 2: {"name": "Mouse", "price": 29.99}}
_next_id = 3


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    return _items[item_id]


@app.get("/items/stats")
def item_stats():
    return {"count": len(_items), "total_value": sum(i["price"] for i in _items.values())}


@app.get("/items")
def list_items():
    return list(_items.values())