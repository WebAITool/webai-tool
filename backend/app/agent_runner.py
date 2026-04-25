import asyncio
import os
import sys
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from fastapi import WebSocket

from app.schemas import TaskStatus, AgentEvent
from app import models

logger = logging.getLogger(__name__)

# Add agent source directory to Python path so lg_agent can be imported
AGENT_SRC_DIR = os.getenv("AGENT_SRC_DIR", "")
if AGENT_SRC_DIR and AGENT_SRC_DIR not in sys.path:
    sys.path.insert(0, AGENT_SRC_DIR)

# In-memory store for active agent runners/tasks
active_tasks: Dict[str, "AgentTask"] = {}


def _parse_last_action(actions: List[str]) -> dict:
    """Parse the last action string from the agent to extract code, output, etc."""
    if not actions:
        return {}
    action = actions[-1]
    result = {}

    code_match = re.search(r'executed code:\n(.*?)\nresult:', action, re.DOTALL)
    if code_match:
        result['code'] = code_match.group(1).strip()

    output_match = re.search(r'result:\n(.*?)\nTree-sitter:', action, re.DOTALL)
    if output_match:
        result['output'] = output_match.group(1).strip()
        result['success'] = 'code was executed without any errors' in result['output']

    frontend_match = re.search(r'Frontend:\n(.*?)$', action, re.DOTALL)
    if frontend_match:
        result['frontend'] = frontend_match.group(1).strip()

    return result


class ConnectionManager:
    """Manages WebSocket connections for real-time event streaming."""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast(self, task_id: str, event: AgentEvent):
        if task_id in self.active_connections:
            message = {
                "event_type": event.event_type,
                "task_id": event.task_id,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }
            disconnected = []
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                self.disconnect(conn, task_id)


# Global connection manager instance
ws_manager = ConnectionManager()


class AgentTask:
    """Wraps the real LangGraph agent, streaming state updates as WebSocket events."""
    def __init__(self, task_id: str, goal: str, spec: str, prjdir: str,
                 max_steps: int, enable_commits: bool = False):
        self.task_id = task_id
        self.goal = goal
        self.spec = spec
        self.prjdir = prjdir
        self.max_steps = max_steps
        self.enable_commits = enable_commits

        self.status = "pending"
        self.current_step = "idle"
        self.step_number = 0

        self.logs: List[str] = []
        self.events: List[AgentEvent] = []
        self.is_running = False
        self._stop_requested = False
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def run(self):
        """Main entry point: import the real agent and run it in a thread."""
        self.is_running = True
        self.status = "running"
        self.current_step = "thinking"
        self._loop = asyncio.get_running_loop()
        models.update_task_status(self.task_id, "running", "thinking", 0)

        try:
            # Lazy import of the agent module (requires AGENT_SRC_DIR on sys.path)
            from lg_agent import create_agent, get_initial_state

            # Resolve prjdir to absolute path
            workspace_base = os.getenv("WORKSPACE_BASE_DIR", "/workspace")
            if not os.path.isabs(self.prjdir):
                abs_prjdir = os.path.join(workspace_base, self.prjdir)
            else:
                abs_prjdir = self.prjdir

            # Ensure project directory exists before agent starts
            os.makedirs(abs_prjdir, exist_ok=True)

            agent = create_agent(self.enable_commits)
            initial_state = get_initial_state(
                goal=self.goal,
                spec=self.spec,
                prjdir=abs_prjdir,
                max_steps=self.max_steps
            )

            # Run the synchronous LangGraph agent in a thread pool
            await self._loop.run_in_executor(
                self._executor,
                self._run_agent_sync,
                agent,
                initial_state
            )

            # If we exited without being stopped or failed, mark completed
            if self.is_running and self.status == "running":
                self.status = "completed"
                self.current_step = "idle"
                models.update_task_status(self.task_id, "completed", "idle", self.step_number)
                await self._emit_event("goal_achieved", {"final": True, "message": "Task completed"})

        except ImportError as e:
            logger.error(f"Cannot import agent module (AGENT_SRC_DIR={AGENT_SRC_DIR}): {e}")
            self.is_running = False
            self.status = "failed"
            models.update_task_status(self.task_id, "failed", "error", self.step_number)
            await self._emit_event("error", {
                "message": f"Agent module not found. Set AGENT_SRC_DIR env var to the webai-tool/src directory. Error: {e}",
                "step": "init"
            })
        except Exception as e:
            logger.exception(f"Agent task {self.task_id} failed")
            self.is_running = False
            self.status = "failed"
            models.update_task_status(self.task_id, "failed", "error", self.step_number)
            await self._emit_event("error", {"message": str(e), "step": self.current_step})
        finally:
            self._executor.shutdown(wait=False)

    def _run_agent_sync(self, agent, initial_state):
        """Run the LangGraph agent synchronously in a thread, streaming state updates."""
        prev_actions_len = 0

        try:
            for chunk in agent.stream(initial_state, config={"recursion_limit": 200}):
                if self._stop_requested:
                    logger.info(f"Task {self.task_id} stop requested, breaking agent loop")
                    break

                # Each chunk is {node_name: state_update_dict}
                for node_name, state_update in chunk.items():
                    self._process_node_output(node_name, state_update, prev_actions_len)

                    # Track action list length for next iteration
                    if 'actions' in state_update:
                        prev_actions_len = len(state_update['actions'])

                    # Update step counter from state_check
                    if 'iter_cnt' in state_update:
                        self.step_number = state_update['iter_cnt']

        except Exception as e:
            logger.exception(f"Agent sync execution failed for task {self.task_id}")
            self.is_running = False
            self.status = "failed"
            models.update_task_status(self.task_id, "failed", "error", self.step_number)
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._emit_event("error", {"message": str(e), "step": self.current_step}),
                    self._loop
                )

    def _process_node_output(self, node_name: str, state_update: dict, prev_actions_len: int):
        """Process a LangGraph node output and emit the appropriate WebSocket events."""
        loop = self._loop
        if not loop:
            return

        if node_name == 'think':
            self.current_step = "thinking"
            models.update_task_status(self.task_id, "running", "thinking", self.step_number)
            plan = state_update.get('plan', '')
            thoughts = state_update.get('thoughts', [])
            recap = thoughts[-2][:200] if len(thoughts) >= 2 else ''
            asyncio.run_coroutine_threadsafe(
                self._emit_event("thinking", {"plan": plan[:1000], "recap": recap}),
                loop
            )
            self.logs.append(f"[thinking] {plan[:500]}")

        elif node_name == 'state_check':
            self.current_step = "state_check"
            decision = state_update.get('decision', '')
            asyncio.run_coroutine_threadsafe(
                self._emit_event("state_check", {"decision": decision}),
                loop
            )
            # If max steps reached, agent will end
            if decision == '__end__':
                self.is_running = False
                self.status = "stopped"
                self.current_step = "idle"
                models.update_task_status(self.task_id, "stopped", "idle", self.step_number)
                asyncio.run_coroutine_threadsafe(
                    self._emit_event("error", {"message": "Max steps reached", "step": "state_check"}),
                    loop
                )

        elif node_name == 'try_to_end':
            decision = state_update.get('decision', '')
            if decision == '__end__':
                # Goal confirmed achieved
                self.is_running = False
                self.status = "completed"
                self.current_step = "idle"
                models.update_task_status(self.task_id, "completed", "idle", self.step_number)
                asyncio.run_coroutine_threadsafe(
                    self._emit_event("goal_achieved", {"final": True, "message": "Goal achieved and verified"}),
                    loop
                )
            else:
                # Not confirmed, will go back to code_action
                asyncio.run_coroutine_threadsafe(
                    self._emit_event("state_check", {"decision": "not_confirmed", "detail": "Goal not yet confirmed"}),
                    loop
                )

        elif node_name == 'code_action':
            actions = state_update.get('actions', [])
            if actions and len(actions) > prev_actions_len:
                # Emit code_writing event
                self.current_step = "code_writing"
                models.update_task_status(self.task_id, "running", "code_writing", self.step_number)
                parsed = _parse_last_action(actions)

                if parsed.get('code'):
                    asyncio.run_coroutine_threadsafe(
                        self._emit_event("code_writing", {"code": parsed['code'][:5000]}),
                        loop
                    )

                # Emit code_executing event
                self.current_step = "code_executing"
                models.update_task_status(self.task_id, "running", "code_executing", self.step_number)

                if parsed.get('output'):
                    asyncio.run_coroutine_threadsafe(
                        self._emit_event("code_executing", {
                            "output": parsed['output'][:3000],
                            "success": parsed.get('success', False)
                        }),
                        loop
                    )
                    self.logs.append(f"[code_executing] {parsed['output'][:500]}")

                # Emit frontend_verify event if UI verification ran
                if parsed.get('frontend'):
                    frontend_text = parsed['frontend']
                    if 'PASSED' in frontend_text:
                        verify_status = 'OK'
                    elif 'ISSUES' in frontend_text or 'error' in frontend_text.lower():
                        verify_status = 'NEEDS_WORK'
                    else:
                        verify_status = 'OK'

                    self.current_step = "frontend_verify"
                    asyncio.run_coroutine_threadsafe(
                        self._emit_event("frontend_verify", {
                            "route": "all",
                            "analysis": frontend_text[:500],
                            "status": verify_status
                        }),
                        loop
                    )

                # If code was not executed (too many failed attempts)
                if not parsed.get('output') and not parsed.get('code'):
                    last_action = actions[-1]
                    asyncio.run_coroutine_threadsafe(
                        self._emit_event("error", {
                            "message": f"Code action failed: {last_action[:300]}",
                            "step": "code_action"
                        }),
                        loop
                    )

        elif node_name == 'commit':
            actions = state_update.get('actions', [])
            if actions and len(actions) > prev_actions_len:
                last_action = actions[-1]
                asyncio.run_coroutine_threadsafe(
                    self._emit_event("code_writing", {"code": f"# Git commit: {last_action[:300]}"}),
                    loop
                )
                self.logs.append(f"[commit] {last_action[:500]}")

    async def _emit_event(self, event_type: str, data: dict):
        """Create an event, store it, and broadcast it via WebSocket."""
        event = AgentEvent(
            task_id=self.task_id,
            event_type=event_type,  # type: ignore
            timestamp=datetime.now(),
            data=data
        )
        self.events.append(event)
        await ws_manager.broadcast(self.task_id, event)

    def stop(self):
        """Signal the task to stop."""
        self._stop_requested = True
        self.is_running = False
        self.status = "stopped"
        models.update_task_status(self.task_id, "stopped", "idle", self.step_number)


# Public API functions for the routes

def get_active_task(task_id: str) -> Optional[AgentTask]:
    return active_tasks.get(task_id)

def create_and_start_task(task_id: str, goal: str, spec: str, prjdir: str,
                          max_steps: int, enable_commits: bool = False) -> AgentTask:
    """Initialize a task object and schedule its execution with the real agent."""
    if task_id in active_tasks:
        return active_tasks[task_id]

    task = AgentTask(task_id, goal, spec, prjdir, max_steps, enable_commits)
    active_tasks[task_id] = task

    # Schedule the async run in the background
    asyncio.create_task(task.run())

    return task
