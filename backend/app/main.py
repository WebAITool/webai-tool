from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import logging

from app.routes import tasks
from app.routes import agent
from app.routes import files
from app.routes import verification
from app.routes import settings

logger = logging.getLogger(__name__)

# Set up agent source directory on Python path at startup
agent_src_dir = os.getenv("AGENT_SRC_DIR", "")
if agent_src_dir and agent_src_dir not in sys.path:
    sys.path.insert(0, agent_src_dir)
    logger.info(f"Added AGENT_SRC_DIR to sys.path: {agent_src_dir}")

# Initialize FastAPI app
app = FastAPI(title="WebAI Tool API", version="1.0.0", redirect_slashes=False)

# Configure CORS
# Get allowed origins from environment variable or use defaults
cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:5173")
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(tasks.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(verification.router, prefix="/api")
app.include_router(settings.router, prefix="/api")

# Health check endpoint
@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "WebAI Tool Backend API"}
