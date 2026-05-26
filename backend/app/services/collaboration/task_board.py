import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from app.models.task import Task, TaskStatus, Priority, RiskLevel


class TaskBoard:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Task]] = {}  # project_id -> task_id -> Task
        self._status_index: Dict[str, Dict[TaskStatus, List[str]]] = {}  # project_id -> status -> task_ids
        self._agent_tasks: Dict[str, Dict[str, List[str]]] = {}  # project_id -> agent_id -> task_ids
        self._task_handlers: Dict[str, List[Callable]] = {}
        self._lock = None
        self._db = None

    def initialize(self, db_service) -> None:
        self._db = db_service

    async def load_all(self) -> None:
        if self._db:
            loaded = await self._db.load_all()
            for pid, tasks_dict in loaded.items():
                self._ensure_project(pid)
                for task_id, task in tasks_dict.items():
                    self._tasks[pid][task_id] = task
                    self._status_index[pid][task.status].append(task_id)
                    for agent_id in task.assigned_agents:
                        if agent_id not in self._agent_tasks[pid]:
                            self._agent_tasks[pid][agent_id] = []
                        self._agent_tasks[pid][agent_id].append(task_id)

    def _ensure_project(self, project_id: str) -> None:
        if project_id not in self._tasks:
            self._tasks[project_id] = {}
            self._status_index[project_id] = {status: [] for status in TaskStatus}
            self._agent_tasks[project_id] = {}

    async def create_task(
        self,
        project_id: str,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        assigned_agents: List[str] = None,
        created_by: str = "system",
        tags: List[str] = None,
        dependencies: List[str] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> Task:
        self._ensure_project(project_id)
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=title,
            description=description,
            project_id=project_id,
            priority=priority,
            risk_level=risk_level,
            assigned_agents=assigned_agents or [],
            created_by=created_by,
            tags=tags or [],
            dependencies=dependencies or [],
        )
        self._tasks[project_id][task_id] = task
        self._status_index[project_id][task.status].append(task_id)
        for agent_id in task.assigned_agents:
            if agent_id not in self._agent_tasks[project_id]:
                self._agent_tasks[project_id][agent_id] = []
            self._agent_tasks[project_id][agent_id].append(task_id)
        self._notify_handlers(task_id, "created", task)
        if self._db:
            await self._db.save(task)
        return task

    def get_task(self, task_id: str, project_id: Optional[str] = None) -> Optional[Task]:
        if project_id:
            return self._tasks.get(project_id, {}).get(task_id)
        for proj_tasks in self._tasks.values():
            if task_id in proj_tasks:
                return proj_tasks[task_id]
        return None

    async def update_task(
        self,
        task_id: str,
        project_id: Optional[str] = None,
        title: str = None,
        description: str = None,
        priority: Priority = None,
        tags: List[str] = None,
        dependencies: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Task]:
        task = self.get_task(task_id, project_id)
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
        if dependencies is not None:
            task.dependencies = dependencies
        if metadata is not None:
            task.metadata = metadata
        task.updated_at = datetime.now()
        self._notify_handlers(task_id, "updated", task)
        if self._db:
            await self._db.save(task)
        return task

    async def assign_agents(self, task_id: str, agent_ids: List[str], project_id: Optional[str] = None) -> Optional[Task]:
        task = self.get_task(task_id, project_id)
        if not task:
            return None
        pid = task.project_id or project_id
        if pid and pid in self._agent_tasks:
            for old_agent in task.assigned_agents:
                if old_agent in self._agent_tasks[pid] and task_id in self._agent_tasks[pid][old_agent]:
                    self._agent_tasks[pid][old_agent].remove(task_id)
        task.assigned_agents = agent_ids
        if pid:
            self._ensure_project(pid)
            for agent_id in agent_ids:
                if agent_id not in self._agent_tasks[pid]:
                    self._agent_tasks[pid][agent_id] = []
                if task_id not in self._agent_tasks[pid][agent_id]:
                    self._agent_tasks[pid][agent_id].append(task_id)
        task.updated_at = datetime.now()
        self._notify_handlers(task_id, "agents_assigned", task)
        if self._db:
            await self._db.save(task)
        return task

    async def change_status(self, task_id: str, new_status: TaskStatus, changed_by: str = "system", project_id: Optional[str] = None) -> Optional[Task]:
        task = self.get_task(task_id, project_id)
        if not task:
            return None
        pid = task.project_id or project_id
        old_status = task.status
        if new_status == old_status:
            return task
        valid_transitions = task.get_valid_transitions()
        if new_status not in valid_transitions:
            raise ValueError(f"Invalid status transition from {old_status.value} to {new_status.value}")
        if pid and pid in self._status_index:
            if task_id in self._status_index[pid].get(old_status, []):
                self._status_index[pid][old_status].remove(task_id)
            self._status_index[pid][new_status].append(task_id)
        task.status = new_status
        task.updated_at = datetime.now()
        task.add_history(
            f"Status changed from {old_status.value} to {new_status.value}",
            changed_by
        )

        # 记录状态流转到 project.log
        try:
            from app.services.project.workspace_manager import workspace_manager
            if pid:
                workspace_manager.add_log(pid, "info", "task_board",
                    f"任务「{task.title}」状态: {old_status.value} → {new_status.value} (by {changed_by})")
        except Exception:
            pass

        self._notify_handlers(task_id, "status_changed", task)
        if self._db:
            await self._db.save(task)
        return task

    async def add_comment(self, task_id: str, comment: str, author: str = "system", project_id: Optional[str] = None) -> Optional[Task]:
        task = self.get_task(task_id, project_id)
        if not task:
            return None
        task.add_history(comment, author)
        self._notify_handlers(task_id, "comment_added", task)
        if self._db:
            await self._db.save(task)
        return task

    async def delete_task(self, task_id: str, project_id: Optional[str] = None) -> bool:
        task = self.get_task(task_id, project_id)
        if not task:
            return False
        pid = task.project_id or project_id
        if pid and pid in self._status_index:
            if task_id in self._status_index[pid].get(task.status, []):
                self._status_index[pid][task.status].remove(task_id)
            for agent_id in task.assigned_agents:
                if agent_id in self._agent_tasks.get(pid, {}) and task_id in self._agent_tasks[pid][agent_id]:
                    self._agent_tasks[pid][agent_id].remove(task_id)
        if pid and pid in self._tasks:
            del self._tasks[pid][task_id]
        self._notify_handlers(task_id, "deleted", None)
        if self._db:
            await self._db.delete(task_id)
        return True

    def list_tasks(
        self,
        project_id: Optional[str] = None,
        status: TaskStatus = None,
        priority: Priority = None,
        assigned_agent: str = None,
        tags: List[str] = None,
        created_by: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        if project_id:
            tasks = list(self._tasks.get(project_id, {}).values())
        else:
            tasks = [t for proj in self._tasks.values() for t in proj.values()]
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

    def get_tasks_by_status(self, status: TaskStatus, project_id: Optional[str] = None) -> List[Task]:
        if project_id:
            task_ids = self._status_index.get(project_id, {}).get(status, [])
            tasks_dict = self._tasks.get(project_id, {})
            return [tasks_dict[tid] for tid in task_ids if tid in tasks_dict]
        result = []
        for pid in self._tasks:
            task_ids = self._status_index.get(pid, {}).get(status, [])
            tasks_dict = self._tasks[pid]
            result.extend(tasks_dict[tid] for tid in task_ids if tid in tasks_dict)
        return result

    def get_tasks_by_agent(self, agent_id: str, project_id: Optional[str] = None) -> List[Task]:
        if project_id:
            task_ids = self._agent_tasks.get(project_id, {}).get(agent_id, [])
            tasks_dict = self._tasks.get(project_id, {})
            return [tasks_dict[tid] for tid in task_ids if tid in tasks_dict]
        result = []
        for pid in self._tasks:
            task_ids = self._agent_tasks.get(pid, {}).get(agent_id, [])
            tasks_dict = self._tasks[pid]
            result.extend(tasks_dict[tid] for tid in task_ids if tid in tasks_dict)
        return result

    def get_tasks_by_board(self, project_id: Optional[str] = None) -> Dict[TaskStatus, List[Task]]:
        return {status: self.get_tasks_by_status(status, project_id) for status in TaskStatus}

    def get_task_count(self, status: TaskStatus = None, project_id: Optional[str] = None) -> int:
        if project_id:
            if status is not None:
                return len(self._status_index.get(project_id, {}).get(status, []))
            return len(self._tasks.get(project_id, {}))
        if status is not None:
            return sum(len(idx.get(status, [])) for idx in self._status_index.values())
        return sum(len(t) for t in self._tasks.values())

    def search_tasks(self, query: str, project_id: Optional[str] = None) -> List[Task]:
        query_lower = query.lower()
        if project_id:
            tasks_dict = self._tasks.get(project_id, {})
            return [
                task for task in tasks_dict.values()
                if query_lower in task.title.lower() or query_lower in task.description.lower()
            ]
        return [
            task for proj_tasks in self._tasks.values()
            for task in proj_tasks.values()
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
        self._status_index.clear()
        self._agent_tasks.clear()

    async def clear_project_tasks(self, project_id: str) -> None:
        """清理指定项目的所有任务"""
        self._tasks.pop(project_id, None)
        self._status_index.pop(project_id, None)
        self._agent_tasks.pop(project_id, None)
        if self._db:
            await self._db.delete_by_project(project_id)


task_board = TaskBoard()
