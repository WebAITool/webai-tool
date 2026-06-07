import os
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

SECRET = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = "HS256"
EXPIRY_HOURS = 24

security = HTTPBearer()

# In-memory user store: username -> {id, password_hash}
_users: dict = {}
_next_user_id = 1


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


def _create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def register_user(data: UserRegister) -> dict:
    global _next_user_id
    if data.username in _users:
        raise HTTPException(status_code=400, detail="Username already exists")
    user_id = _next_user_id
    _next_user_id += 1
    _users[data.username] = {"id": user_id, "password": data.password}
    token = _create_token(data.username)
    return {"id": user_id, "username": data.username, "token": token}


def login_user(data: UserLogin) -> dict:
    user = _users.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_token(data.username)
    return {"token": token}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in _users:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
