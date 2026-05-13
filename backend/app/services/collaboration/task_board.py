import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum

from app.models.task import Task, TaskStatus, Priority


class TaskBoard:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._status_index: Dict[TaskStatus, List[str]] = {status: [] for status in TaskStatus}
        self._agent_tasks: Dict[str, List[str]] = {}
        self._task_handlers: Dict[str, List[Callable]] = {}
        self._lock = None

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        assigned_agents: List[str] = None,
        created_by: str = "system",
        tags: List[str] = None
    ) -> Task:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            assigned_agents=assigned_agents or [],
            created_by=created_by,
            tags=tags or []
        )
        self._tasks[task_id] = task
        self._status_index[task.status].append(task_id)
        for agent_id in task.assigned_agents:
            if agent_id not in self._agent_tasks:
                self._agent_tasks[agent_id] = []
            self._agent_tasks[agent_id].append(task_id)
        self._notify_handlers(task_id, "created", task)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        title: str = None,
        description: str = None,
        priority: Priority = None,
        tags: List[str] = None
    ) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if tags is not None:
            task.tags = tags
        task.updated_at = datetime.now()
        self._notify_handlers(task_id, "updated", task)
        return task

    def assign_agents(self, task_id: str, agent_ids: List[str]) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        for old_agent in task.assigned_agents:
            if old_agent in self._agent_tasks and task_id in self._agent_tasks[old_agent]:
                self._agent_tasks[old_agent].remove(task_id)
        task.assigned_agents = agent_ids
        for agent_id in agent_ids:
            if agent_id not in self._agent_tasks:
                self._agent_tasks[agent_id] = []
            if task_id not in self._agent_tasks[agent_id]:
                self._agent_tasks[agent_id].append(task_id)
        task.updated_at = datetime.now()
        self._notify_handlers(task_id, "agents_assigned", task)
        return task

    def change_status(self, task_id: str, new_status: TaskStatus, changed_by: str = "system") -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        old_status = task.status
        if new_status == old_status:
            return task
        valid_transitions = task.get_valid_transitions()
        if new_status not in valid_transitions:
            raise ValueError(f"Invalid status transition from {old_status.value} to {new_status.value}")
        self._status_index[old_status].remove(task_id)
        task.status = new_status
        self._status_index[new_status].append(task_id)
        task.updated_at = datetime.now()
        task.add_history(
            f"Status changed from {old_status.value} to {new_status.value}",
            changed_by
        )
        self._notify_handlers(task_id, "status_changed", task)
        return task

    def add_comment(self, task_id: str, comment: str, author: str = "system") -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.add_history(comment, author)
        self._notify_handlers(task_id, "comment_added", task)
        return task

    def delete_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        self._status_index[task.status].remove(task_id)
        for agent_id in task.assigned_agents:
            if agent_id in self._agent_tasks and task_id in self._agent_tasks[agent_id]:
                self._agent_tasks[agent_id].remove(task_id)
        del self._tasks[task_id]
        self._notify_handlers(task_id, "deleted", None)
        return True

    def list_tasks(
        self,
        status: TaskStatus = None,
        priority: Priority = None,
        assigned_agent: str = None,
        tags: List[str] = None,
        created_by: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        if assigned_agent is not None:
            tasks = [t for t in tasks if assigned_agent in t.assigned_agents]
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]
        if created_by is not None:
            tasks = [t for t in tasks if t.created_by == created_by]
        tasks.sort(key=lambda t: (-t.priority.sort_value, t.created_at))
        return tasks[offset:offset + limit]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        task_ids = self._status_index.get(status, [])
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

    def get_tasks_by_agent(self, agent_id: str) -> List[Task]:
        task_ids = self._agent_tasks.get(agent_id, [])
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

    def get_tasks_by_board(self) -> Dict[TaskStatus, List[Task]]:
        return {status: self.get_tasks_by_status(status) for status in TaskStatus}

    def get_task_count(self, status: TaskStatus = None) -> int:
        if status is not None:
            return len(self._status_index.get(status, []))
        return len(self._tasks)

    def search_tasks(self, query: str) -> List[Task]:
        query_lower = query.lower()
        return [
            task for task in self._tasks.values()
            if query_lower in task.title.lower() or query_lower in task.description.lower()
        ]

    def register_handler(self, event: str, handler: Callable) -> None:
        if event not in self._task_handlers:
            self._task_handlers[event] = []
        self._task_handlers[event].append(handler)

    def unregister_handler(self, event: str, handler: Callable) -> None:
        if event in self._task_handlers and handler in self._task_handlers[event]:
            self._task_handlers[event].remove(handler)

    def _notify_handlers(self, task_id: str, event: str, task: Optional[Task]) -> None:
        if event in self._task_handlers:
            for handler in self._task_handlers[event]:
                try:
                    handler(task_id, event, task)
                except Exception:
                    pass

    def clear_all(self) -> None:
        self._tasks.clear()
        self._status_index = {status: [] for status in TaskStatus}
        self._agent_tasks.clear()


task_board = TaskBoard()
