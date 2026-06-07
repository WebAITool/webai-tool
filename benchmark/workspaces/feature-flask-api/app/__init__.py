from flask import Flask, request, jsonify
from flask import request
from app.models import Item, _items, _next_id
import math

app = Flask(__name__)


@app.route("/items", methods=["GET"])
def list_items():
    items = list(_items.values())
    q = request.args.get("q")
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)

    # No query parameters -> return flat list (backward compatible)
    if q is None and page is None and per_page is None:
        return jsonify([i.to_dict() for i in items])

    # Apply search filter
    if q:
        q_lower = q.lower()
        items = [i for i in items if q_lower in i.name.lower()]

    # Apply pagination
    total = len(items)
    if per_page is None:
        per_page = 10
    if page is None:
        page = 1
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    start = (page - 1) * per_page
    end = start + per_page
    items_page = items[start:end]

    return jsonify({
        "items": [i.to_dict() for i in items_page],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages
    })

@app.route("/items", methods=["POST"])
def create_item():
    global _next_id
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    item = Item(id=_next_id, name=data["name"], price=data.get("price", 0))
    _items[_next_id] = item
    _next_id += 1
    return jsonify(item.to_dict()), 201


@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = _items.get(item_id)
    if not item:
        return jsonify({"error": "not found"}), 404
    return jsonify(item.to_dict())


@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    if item_id in _items:
        del _items[item_id]
        return "", 204
    return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
