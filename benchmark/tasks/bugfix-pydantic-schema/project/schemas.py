"""Pydantic schemas with validation bugs."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str  # BUG: no min_length
    email: str     # BUG: no EmailStr validation
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    password_hash: str  # BUG: should not be in response
    created_at: Optional[datetime] = None


class ItemCreate(BaseModel):
    name: str
    price: float  # BUG: no ge=0 constraint
    description: str = ""


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    # BUG: missing created_at field
