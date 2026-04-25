from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from typing import List
import asyncio

from app.schemas import TaskStatus, AgentEvent
from app import models
from app import agent_runner

router = APIRouter(prefix="/agent", tags=["agent"])

@router.post("/{task_id}/start", response_model=TaskStatus)
async def start_agent(task_id: str):
    """
    Start agent execution for a task.
    """
    # Verify task exists in DB
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    # Check API key is configured
    settings = models.get_settings()
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is not configured. Set it in the Settings page."
        )
    
    # Check if already running
    active_task = agent_runner.get_active_task(task_id)
    if active_task and active_task.is_running:
        return task # Already running, return current status

    # Create and start the runner with real agent
    agent_runner.create_and_start_task(
        task_id=task.id,
        goal=task.goal,
        spec=task.spec,
        prjdir=task.prjdir,
        max_steps=task.max_steps,
        enable_commits=task.enable_commits
    )
    
    # Return updated status
    return models.get_task(task_id)

@router.post("/{task_id}/stop", response_model=TaskStatus)
async def stop_agent(task_id: str):
    """
    Stop a running agent.
    """
    active_task = agent_runner.get_active_task(task_id)
    if not active_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active task not found")
    
    active_task.stop()
    
    # Return the stopped status from the DB or active task
    return models.get_task(task_id)

@router.get("/{task_id}/status", response_model=TaskStatus)
async def get_agent_status(task_id: str):
    """
    Get current agent state.
    """
    # Check active runners for real-time data
    active_task = agent_runner.get_active_task(task_id)
    if active_task:
        # Merge DB task with runtime state
        base_task = models.get_task(task_id)
        if base_task:
            return base_task.model_copy(update={
                "status": active_task.status,
                "current_step": active_task.current_step,
                "step_number": active_task.step_number
            })
    
    # Fallback to DB
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task

@router.get("/{task_id}/logs")
async def get_agent_logs(task_id: str):
    """
    Get full execution logs as plain text.
    """
    active_task = agent_runner.get_active_task(task_id)
    if active_task:
        return "\n".join(active_task.logs)
    
    # If task is not active, we might want to retrieve logs from a file or DB
    # For this implementation, we return a message indicating no active logs
    return "Task is not currently running or logs are not available in memory."

@router.get("/{task_id}/actions", response_model=List[AgentEvent])
async def get_agent_actions(task_id: str):
    """
    Get list of all actions taken by the agent.
    """
    active_task = agent_runner.get_active_task(task_id)
    if active_task:
        return active_task.events
    return []

@router.websocket("/{task_id}")
async def websocket_agent(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time event streaming.
    """
    await agent_runner.ws_manager.connect(websocket, task_id)
    
    try:
        # Send historical events immediately upon connection
        active_task = agent_runner.get_active_task(task_id)
        if active_task:
            for event in active_task.events:
                await websocket.send_json({
                    "event_type": event.event_type,
                    "task_id": event.task_id,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data
                })
        
        # Keep connection open to listen for close or handle pings
        while True:
            # Just keeping the connection alive. 
            # In a production app, you might handle incoming messages from client here.
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        agent_runner.ws_manager.disconnect(websocket, task_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        agent_runner.ws_manager.disconnect(websocket, task_id)
