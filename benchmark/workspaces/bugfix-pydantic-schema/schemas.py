"""Pydantic schemas with validation bugs."""
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: Optional[datetime] = None


class ItemCreate(BaseModel):
    name: str
    price: float = Field(ge=0)
    description: str = ""


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    created_at: datetime | None = None
    # BUG: missing created_at field
