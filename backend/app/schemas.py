from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class TaskCreate(BaseModel):
    goal: str
    spec: str
    prjdir: str
    max_steps: int = 50
    enable_commits: bool = False
    commit_branch: str = "dev"

class TaskStatus(BaseModel):
    id: str
    goal: str
    status: Literal["pending", "running", "completed", "failed", "stopped"]
    current_step: str
    step_number: int
    max_steps: int
    created_at: datetime
    updated_at: datetime
    prjdir: str
    spec: str = ""
    enable_commits: bool = False

class AgentEvent(BaseModel):
    task_id: str
    event_type: Literal["thinking", "code_writing", "code_executing", "frontend_verify", "goal_achieved", "error", "screenshot", "state_check"]
    timestamp: datetime
    data: dict

class FileNode(BaseModel):
    name: str
    path: str
    is_directory: bool
    children: Optional[List["FileNode"]] = None
    size: Optional[int] = None
    modified_at: Optional[datetime] = None

class VerificationResult(BaseModel):
    route: str
    screenshot_path: str
    screenshot_base64: Optional[str] = None
    analysis: str
    status: Literal["OK", "NEEDS_WORK", "BROKEN"]

class SettingsData(BaseModel):
    api_key: str = ""
    api_base_url: str = "https://api.polza.ai/api/v1"
    model_name: str = "z-ai/glm-4.7"
    max_steps: int = 50
    patience: int = 3
    action_memory: bool = True
    enable_frontend_verify: bool = True
    headless_mode: bool = True
    verify_port: int = 5173
