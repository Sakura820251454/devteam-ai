import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models.execution_db import TaskExecutionModel, TaskCheckpointModel

logger = logging.getLogger(__name__)


class TaskPersistenceService:
    """任务执行状态和检查点的持久化服务"""

    def __init__(self):
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def _get_session(self) -> AsyncSession:
        if not self._session_maker:
            raise RuntimeError("TaskPersistenceService not initialized")
        return self._session_maker()

    async def save_execution(
        self,
        task_id: str,
        agent_id: str,
        status: str,
        current_step_index: int = 0,
        total_steps: int = 1,
        accumulated_result: str = None,
        checkpoint_data: Dict = None,
    ) -> str:
        """保存或更新任务执行状态"""
        async with await self._get_session() as db:
            existing = await db.execute(
                select(TaskExecutionModel).where(TaskExecutionModel.task_id == task_id)
            )
            model = existing.scalar_one_or_none()

            if model:
                model.status = status
                model.current_step_index = current_step_index
                model.total_steps = total_steps
                if accumulated_result is not None:
                    model.accumulated_result = accumulated_result
                if checkpoint_data is not None:
                    model.checkpoint_data = checkpoint_data
                model.last_heartbeat_at = datetime.now()
                model.updated_at = datetime.now()
            else:
                model = TaskExecutionModel(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    agent_id=agent_id,
                    status=status,
                    current_step_index=current_step_index,
                    total_steps=total_steps,
                    accumulated_result=accumulated_result,
                    checkpoint_data=checkpoint_data or {},
                    last_heartbeat_at=datetime.now(),
                    started_at=datetime.now(),
                )
                db.add(model)

            await db.commit()
            return model.id

    async def load_execution(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从数据库加载任务执行状态"""
        async with await self._get_session() as db:
            result = await db.execute(
                select(TaskExecutionModel).where(TaskExecutionModel.task_id == task_id)
            )
            model = result.scalar_one_or_none()
            if not model:
                return None

            return {
                "task_id": model.task_id,
                "agent_id": model.agent_id,
                "status": model.status,
                "current_step_index": model.current_step_index,
                "total_steps": model.total_steps,
                "last_heartbeat": model.last_heartbeat_at,
                "accumulated_result": model.accumulated_result,
                "checkpoint_data": model.checkpoint_data,
                "started_at": model.started_at,
                "paused_at": model.paused_at,
                "completed_at": model.completed_at,
            }

    async def save_checkpoint(
        self,
        task_id: str,
        step_index: int,
        step_name: str = "",
        context: Dict = None,
        partial_result: str = None,
        extra_data: Dict = None,
    ) -> str:
        """保存检查点"""
        checkpoint_id = str(uuid.uuid4())
        async with await self._get_session() as db:
            model = TaskCheckpointModel(
                id=checkpoint_id,
                task_id=task_id,
                step_index=step_index,
                step_name=step_name,
                context=context or {},
                partial_result=partial_result,
                extra_data=extra_data or {},
            )
            db.add(model)
            await db.commit()
            return checkpoint_id

    async def load_latest_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """加载任务的最新检查点"""
        async with await self._get_session() as db:
            result = await db.execute(
                select(TaskCheckpointModel)
                .where(TaskCheckpointModel.task_id == task_id)
                .order_by(TaskCheckpointModel.step_index.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()
            if not model:
                return None

            return {
                "id": model.id,
                "task_id": model.task_id,
                "step_index": model.step_index,
                "step_name": model.step_name,
                "context": model.context,
                "partial_result": model.partial_result,
                "metadata": model.extra_data,
                "created_at": model.created_at,
            }

    async def list_checkpoints(self, task_id: str) -> List[Dict[str, Any]]:
        """列出任务的所有检查点"""
        async with await self._get_session() as db:
            result = await db.execute(
                select(TaskCheckpointModel)
                .where(TaskCheckpointModel.task_id == task_id)
                .order_by(TaskCheckpointModel.step_index.asc())
            )
            models = result.scalars().all()
            return [
                {
                    "id": m.id,
                    "task_id": m.task_id,
                    "step_index": m.step_index,
                    "step_name": m.step_name,
                    "context": m.context,
                    "partial_result": m.partial_result,
                    "metadata": m.extra_data,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in models
            ]

    async def update_heartbeat(self, task_id: str, step_index: int, total_steps: int) -> None:
        """更新心跳时间戳"""
        async with await self._get_session() as db:
            result = await db.execute(
                select(TaskExecutionModel).where(TaskExecutionModel.task_id == task_id)
            )
            model = result.scalar_one_or_none()
            if model:
                model.last_heartbeat_at = datetime.now()
                model.current_step_index = step_index
                model.total_steps = total_steps
                model.heartbeat_count = (model.heartbeat_count or 0) + 1
                await db.commit()

    async def delete_execution(self, task_id: str) -> None:
        """删除任务执行记录"""
        async with await self._get_session() as db:
            result = await db.execute(
                select(TaskExecutionModel).where(TaskExecutionModel.task_id == task_id)
            )
            model = result.scalar_one_or_none()
            if model:
                await db.delete(model)
                await db.commit()


task_persistence_service = TaskPersistenceService()
