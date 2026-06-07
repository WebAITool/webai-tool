from fastapi import FastAPI
from app.routes import users

app = FastAPI()
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/health")
def health():
    return {"status": "ok"}
