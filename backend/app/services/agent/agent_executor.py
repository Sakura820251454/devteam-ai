import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Callable, Any
from enum import Enum

from app.models.agent import AgentStatus
from app.models.task import Task, TaskStatus
from app.services.collaboration.task_board import task_board
from app.services.collaboration.message_bus import message_bus, Message, MessageType
from app.services.collaboration.speaking_controller import speaking_controller, SpeakingMode


class ExecutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecutor:
    def __init__(self):
        self._running_tasks: Dict[str, Dict[str, Any]] = {}
        self._agent_tasks: Dict[str, str] = {}
        self._execution_handlers: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._global_paused: bool = False

    async def assign_task(
        self,
        task_id: str,
        agent_id: str,
        agent_execute_fn: Callable
    ) -> bool:
        async with self._lock:
            task = task_board.get_task(task_id)
            if not task:
                return False

            if task.status not in [TaskStatus.TODO, TaskStatus.BACKLOG]:
                return False

            self._agent_tasks[agent_id] = task_id
            self._running_tasks[task_id] = {
                "agent_id": agent_id,
                "execute_fn": agent_execute_fn,
                "status": ExecutionStatus.IDLE,
                "started_at": None,
                "completed_at": None
            }

            task_board.assign_agents(task_id, [agent_id])
            return True

    async def start_execution(self, task_id: str) -> bool:
        async with self._lock:
            execution = self._running_tasks.get(task_id)
            if not execution:
                return False

            if self._global_paused:
                execution["status"] = ExecutionStatus.PAUSED
                return False

            execution["status"] = ExecutionStatus.RUNNING
            execution["started_at"] = datetime.now()

            task = task_board.get_task(task_id)
            if task:
                try:
                    task_board.change_status(task_id, TaskStatus.IN_PROGRESS, "system")
                except ValueError:
                    pass

            asyncio.create_task(self._execute_task(task_id))
            return True

    async def _execute_task(self, task_id: str) -> None:
        execution = self._running_tasks.get(task_id)
        if not execution:
            return

        task = task_board.get_task(task_id)
        if not task:
            return

        msg = Message(
            sender_id="system",
            sender_name="System",
            channel=f"task:{task_id}",
            content=f"Agent {execution['agent_id']} 开始执行任务: {task.title}",
            message_type=MessageType.SYSTEM
        )
        await message_bus.send_to_task(msg, task_id)

        try:
            result = await execution["execute_fn"](task)

            if result.get("success", False):
                execution["status"] = ExecutionStatus.COMPLETED
                task_board.change_status(task_id, TaskStatus.REVIEW, "system")
                task_board.add_comment(task_id, f"任务完成: {result.get('summary', '')}", "system")
            else:
                execution["status"] = ExecutionStatus.FAILED
                task_board.add_comment(task_id, f"任务失败: {result.get('error', 'Unknown error')}", "system")

        except Exception as e:
            execution["status"] = ExecutionStatus.FAILED
            task_board.add_comment(task_id, f"执行异常: {str(e)}", "system")

        execution["completed_at"] = datetime.now()

    async def pause_execution(self, task_id: str) -> bool:
        async with self._lock:
            execution = self._running_tasks.get(task_id)
            if not execution:
                return False

            execution["status"] = ExecutionStatus.PAUSED
            task = task_board.get_task(task_id)
            if task:
                task_board.change_status(task_id, TaskStatus.PAUSED, "system")
            return True

    async def resume_execution(self, task_id: str) -> bool:
        async with self._lock:
            execution = self._running_tasks.get(task_id)
            if not execution:
                return False

            if execution["status"] != ExecutionStatus.PAUSED:
                return False

            return await self.start_execution(task_id)

    async def cancel_execution(self, task_id: str) -> bool:
        async with self._lock:
            execution = self._running_tasks.get(task_id)
            if not execution:
                return False

            execution["status"] = ExecutionStatus.CANCELLED
            task = task_board.get_task(task_id)
            if task:
                task_board.change_status(task_id, TaskStatus.CANCELLED, "system")

            agent_id = execution["agent_id"]
            if agent_id in self._agent_tasks:
                del self._agent_tasks[agent_id]

            return True

    async def pause_all(self) -> None:
        async with self._lock:
            self._global_paused = True
            for task_id, execution in self._running_tasks.items():
                if execution["status"] == ExecutionStatus.RUNNING:
                    execution["status"] = ExecutionStatus.PAUSED
                    task = task_board.get_task(task_id)
                    if task:
                        task_board.change_status(task_id, TaskStatus.PAUSED, "system")

    async def resume_all(self) -> None:
        async with self._lock:
            self._global_paused = False
            for task_id, execution in self._running_tasks.items():
                if execution["status"] == ExecutionStatus.PAUSED:
                    await self.start_execution(task_id)

    def get_execution_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        execution = self._running_tasks.get(task_id)
        if not execution:
            return None

        return {
            "task_id": task_id,
            "agent_id": execution["agent_id"],
            "status": execution["status"].value,
            "started_at": execution["started_at"].isoformat() if execution["started_at"] else None,
            "completed_at": execution["completed_at"].isoformat() if execution["completed_at"] else None
        }

    def get_agent_current_task(self, agent_id: str) -> Optional[str]:
        return self._agent_tasks.get(agent_id)

    def get_running_tasks(self) -> List[Dict[str, Any]]:
        return [
            self.get_execution_status(task_id)
            for task_id in self._running_tasks.keys()
            if self.get_execution_status(task_id)
        ]

    def is_global_paused(self) -> bool:
        return self._global_paused


agent_executor = AgentExecutor()
