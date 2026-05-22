import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models.core_db import TaskModel
from app.models.task import Task, TaskStatus, TaskHistory, Priority, RiskLevel


class TaskPersistenceService:
    """任务持久化服务 — CRUD for TaskModel"""

    def __init__(self):
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def _get_session(self) -> AsyncSession:
        if not self._session_maker:
            raise RuntimeError("TaskPersistenceService not initialized")
        return self._session_maker()

    async def load_all(self) -> Dict[str, Dict[str, Task]]:
        """Load all tasks, grouped by project_id -> task_id -> Task"""
        async with await self._get_session() as db:
            result = await db.execute(select(TaskModel))
            models = result.scalars().all()
            tasks: Dict[str, Dict[str, Task]] = {}
            for m in models:
                pid = m.project_id
                if pid not in tasks:
                    tasks[pid] = {}
                tasks[pid][m.id] = _task_from_model(m)
            return tasks

    async def save(self, task: Task) -> None:
        async with await self._get_session() as db:
            existing = await db.get(TaskModel, task.id)
            if existing:
                existing.title = task.title
                existing.description = task.description
                existing.status = task.status.value
                existing.priority = task.priority.value
                existing.risk_level = task.risk_level.value
                existing.assigned_agents = task.assigned_agents
                existing.collaborated_agents = task.collaborated_agents
                existing.dependencies = task.dependencies
                existing.linked_documents = task.linked_documents
                existing.tags = task.tags
                existing.history = [h.model_dump(mode='json') for h in task.history]
                existing.approval_required = task.approval_required
                existing.approved_by = task.approved_by
                existing.approved_at = task.approved_at
                existing.updated_at = datetime.now()
                existing.completed_at = task.completed_at
            else:
                db.add(_model_from_task(task))
            await db.commit()

    async def delete(self, task_id: str) -> None:
        async with await self._get_session() as db:
            model = await db.get(TaskModel, task_id)
            if model:
                await db.delete(model)
                await db.commit()

    async def delete_by_project(self, project_id: str) -> None:
        async with await self._get_session() as db:
            result = await db.execute(
                select(TaskModel).where(TaskModel.project_id == project_id)
            )
            for model in result.scalars().all():
                await db.delete(model)
            await db.commit()


def _model_from_task(task: Task) -> TaskModel:
    return TaskModel(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        priority=task.priority.value,
        risk_level=task.risk_level.value,
        assigned_agents=task.assigned_agents,
        collaborated_agents=task.collaborated_agents,
        dependencies=task.dependencies,
        linked_documents=task.linked_documents,
        created_by=task.created_by,
        tags=task.tags,
        history=[h.model_dump(mode='json') for h in task.history],
        approval_required=task.approval_required,
        approved_by=task.approved_by,
        approved_at=task.approved_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
    )


def _task_from_model(model: TaskModel) -> Task:
    return Task(
        id=model.id,
        title=model.title,
        description=model.description or "",
        project_id=model.project_id,
        status=TaskStatus(model.status),
        priority=Priority(model.priority),
        risk_level=RiskLevel(model.risk_level),
        assigned_agents=model.assigned_agents or [],
        collaborated_agents=model.collaborated_agents or [],
        dependencies=model.dependencies or [],
        linked_documents=model.linked_documents or [],
        created_by=model.created_by or "system",
        tags=model.tags or [],
        created_at=model.created_at,
        updated_at=model.updated_at,
        completed_at=model.completed_at,
        history=[TaskHistory(**h) for h in (model.history or [])],
        approval_required=model.approval_required or False,
        approved_by=model.approved_by,
        approved_at=model.approved_at,
    )


task_persistence = TaskPersistenceService()
