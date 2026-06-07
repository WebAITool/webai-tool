import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ----- Configuration -----
SECRET_KEY = "dev-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 hours

# ----- In-memory user store -----
users_db = {}

# ----- Models -----
class AuthRequest(BaseModel):
    username: str
    password: str

# ----- Helper functions -----
def hash_password(password: str) -> str:
    """Return SHA-256 hex digest of the password."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(username: str) -> str:
    """Create a JWT token for the given username."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> str:
    """Extract and validate the token, return the username."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        # Ensure user still exists
        if username not in users_db:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# ----- FastAPI app -----
app = FastAPI()

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Endpoints -----
@app.post("/api/auth/register", status_code=201)
def register(request: AuthRequest):
    """Register a new user and return token."""
    username = request.username
    password = request.password
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    if username in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    users_db[username] = hash_password(password)
    token = create_token(username)
    return {"username": username, "token": token}

@app.post("/api/auth/login")
def login(request: AuthRequest):
    """Authenticate user and return a token."""
    username = request.username
    password = request.password
    if username not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if users_db[username] != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(username)
    return {"token": token}

@app.get("/api/auth/me")
def me(current_user: str = Depends(get_current_user)):
    """Return the current logged-in user's info."""
    return {"username": current_user}

_items = ["item1", "item2", "item3", "item4", "item5", "item6", "item7", "item8", "item9", "item10"]

@app.get("/api/items")
def list_items(current_user: str = Depends(get_current_user)):
    """Return a list of items (protected endpoint)."""
    return _items

# ----- Run with uvicorn if executed directly -----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
