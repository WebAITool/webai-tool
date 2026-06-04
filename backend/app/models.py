from typing import Dict, List, Optional
from datetime import datetime
from app.schemas import TaskStatus, VerificationResult, SettingsData

# In-memory storage for tasks
# Key: task_id (str), Value: TaskStatus object
tasks_db: Dict[str, TaskStatus] = {}

def get_task(task_id: str) -> Optional[TaskStatus]:
    return tasks_db.get(task_id)

def save_task(task: TaskStatus):
    tasks_db[task.id] = task

def delete_task(task_id: str) -> bool:
    if task_id in tasks_db:
        del tasks_db[task_id]
        return True
    return False

def get_all_tasks() -> List[TaskStatus]:
    return list(tasks_db.values())

def update_task_status(task_id: str, status: str, current_step: str = "idle", step_number: int = 0):
    task = get_task(task_id)
    if task:
        # Create a copy of the task with updated fields to handle immutability
        updated_task = task.model_copy(update={
            "status": status,
            "current_step": current_step,
            "step_number": step_number,
            "updated_at": datetime.now()
        })
        save_task(updated_task)
        return updated_task
    return None


# In-memory storage for verification results
# Key: task_id (str), Value: List of VerificationResult objects
verification_results_db: Dict[str, List["VerificationResult"]] = {}

def save_verification_result(task_id: str, result: "VerificationResult"):
    if task_id not in verification_results_db:
        verification_results_db[task_id] = []
    verification_results_db[task_id].append(result)

def get_verification_results(task_id: str) -> List["VerificationResult"]:
    return verification_results_db.get(task_id, [])

def get_verification_result(task_id: str, route: str) -> Optional["VerificationResult"]:
    results = verification_results_db.get(task_id, [])
    for res in results:
        if res.route == route:
            return res
    return None


# In-memory settings storage (initialized from env vars)
import os as _os

_settings: SettingsData = SettingsData(
    api_key=_os.getenv("API_KEY", ""),
    api_base_url=_os.getenv("API_BASE_URL", "https://api.polza.ai/api/v1"),
    model_name=_os.getenv("MODEL_NAME", "z-ai/glm-4.7"),
)

def get_settings() -> SettingsData:
    return _settings

def save_settings(data: SettingsData) -> SettingsData:
    global _settings
    _settings = data
    # Also update env vars so agent_runner can read them
    _os.environ["API_KEY"] = data.api_key
    _os.environ["API_BASE_URL"] = data.api_base_url
    _os.environ["MODEL_NAME"] = data.model_name
    return _settings
