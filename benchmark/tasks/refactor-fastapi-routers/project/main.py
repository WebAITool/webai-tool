"""Monolithic FastAPI app — all routes in one file."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class UserCreate(BaseModel):
    username: str
    email: str

class UserResp(BaseModel):
    id: int
    username: str
    email: str

class ItemCreate(BaseModel):
    name: str
    price: float

class ItemResp(BaseModel):
    id: int
    name: str
    price: float


# --- In-memory stores ---

_users: list = []
_user_next = 1
_items: list = []
_item_next = 1


# --- Health routes ---

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}


# --- User routes ---

@app.get("/users")
def list_users():
    return _users

@app.post("/users", status_code=201)
def create_user(body: UserCreate):
    global _user_next
    user = {"id": _user_next, "username": body.username, "email": body.email}
    _users.append(user)
    _user_next += 1
    return user

@app.get("/users/{user_id}")
def get_user(user_id: int):
    for u in _users:
        if u["id"] == user_id:
            return u
    raise HTTPException(404, "User not found")

@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    global _users
    _users = [u for u in _users if u["id"] != user_id]


# --- Item routes ---

@app.get("/items")
def list_items():
    return _items

@app.post("/items", status_code=201)
def create_item(body: ItemCreate):
    global _item_next
    item = {"id": _item_next, "name": body.name, "price": body.price}
    _items.append(item)
    _item_next += 1
    return item

@app.get("/items/{item_id}")
def get_item(item_id: int):
    for i in _items:
        if i["id"] == item_id:
            return i
    raise HTTPException(404, "Item not found")

@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    global _items
    _items = [i for i in _items if i["id"] != item_id]
