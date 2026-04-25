from fastapi import APIRouter, HTTPException, status
from typing import List
import uuid
from datetime import datetime

from app.schemas import TaskCreate, TaskStatus
from app import models

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", response_model=TaskStatus, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate):
    """
    Create a new agent task (does NOT start execution).
    """
    task_id = str(uuid.uuid4())
    now = datetime.now()
    
    new_task = TaskStatus(
        id=task_id,
        goal=task_data.goal,
        status="pending",
        current_step="idle",
        step_number=0,
        max_steps=task_data.max_steps,
        created_at=now,
        updated_at=now,
        prjdir=task_data.prjdir,
        spec=task_data.spec,
        enable_commits=task_data.enable_commits
    )
    
    models.save_task(new_task)
    return new_task

@router.get("", response_model=List[TaskStatus])
async def list_tasks():
    """
    List all tasks with their statuses.
    """
    return models.get_all_tasks()

@router.get("/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    """
    Get detailed task status.
    """
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    """
    Delete a task and its workspace.
    """
    deleted = models.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    # Note: In a real implementation, we would also clean up the workspace directory here.
    return None
