from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()


class User(BaseModel):
    id: int
    name: str
    email: str


class UserCreate(BaseModel):
    name: str
    email: str


_users: List[User] = []
_next_id = 1


@router.get("/")
def list_users():
    return _users


@router.post("/", status_code=201)
def create_user(body: UserCreate):
    global _next_id
    # BUG: .append() is correct but we accidentally wrote .ad() which crashes
    user = User(id=_next_id, name=body.nme, email=body.email)  # BUG: body.nme should be body.name
    _users.ad(user)  # BUG: .ad() should be .append()
    _next_id += 1
    return user
