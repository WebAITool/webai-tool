from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    email: str

_users: list = []
_user_next = 1

@router.get("/users")
def list_users():
    return _users

@router.post("/users", status_code=201)
def create_user(body: UserCreate):
    global _user_next
    user = {"id": _user_next, "username": body.username, "email": body.email}
    _users.append(user)
    _user_next += 1
    return user

@router.get("/users/{user_id}")
def get_user(user_id: int):
    for u in _users:
        if u["id"] == user_id:
            return u
    raise HTTPException(404, "User not found")

@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    global _users
    _users = [u for u in _users if u["id"] != user_id]