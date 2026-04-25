from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    workspace_base_dir: str = "/workspace"
    agent_src_dir: str = ""
    
    class Config:
        # Look for .env in backend dir first, then project root
        env_file = [
            ".env",
            str(Path(__file__).resolve().parents[3] / ".env")
        ]

settings = Settings()
