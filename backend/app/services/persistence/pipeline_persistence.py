import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models.core_db import PipelineModel
from app.services.collaboration.pipeline_orchestrator import Pipeline, PipelineStatus, PipelineStage


class PipelinePersistenceService:
    """流水线持久化服务 — CRUD for PipelineModel"""

    def __init__(self):
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def _get_session(self) -> AsyncSession:
        if not self._session_maker:
            raise RuntimeError("PipelinePersistenceService not initialized")
        return self._session_maker()

    async def load_all(self) -> Dict[str, Pipeline]:
        async with await self._get_session() as db:
            result = await db.execute(select(PipelineModel))
            models = result.scalars().all()
            pipelines: Dict[str, Pipeline] = {}
            for m in models:
                pipeline = _pipeline_from_model(m)
                if pipeline.status == PipelineStatus.RUNNING:
                    pipeline.status = PipelineStatus.FAILED
                    pipeline.add_log("control", "Pipeline marked as FAILED: server restarted, asyncio task is dead")
                # PAUSED pipelines are kept as-is — they were intentionally saved and can be resumed
                pipelines[pipeline.id] = pipeline
            return pipelines

    async def save(self, pipeline: Pipeline) -> None:
        logs = pipeline.logs
        if len(logs) > 1000:
            logs = logs[-1000:]

        async with await self._get_session() as db:
            existing = await db.get(PipelineModel, pipeline.id)
            if existing:
                existing.name = pipeline.name
                existing.status = pipeline.status.value
                existing.current_stage = pipeline.current_stage.value
                existing.progress = pipeline.progress
                existing.agents = pipeline.agents
                existing.task_ids = pipeline.task_ids
                existing.context = pipeline.context
                existing.logs = logs
                existing.team_config = getattr(pipeline, 'team_config', {})
                existing.agent_roles = getattr(pipeline, 'agent_roles', {})
                existing.stages = getattr(pipeline, 'stages', [])
                existing.paused = pipeline.paused
                existing.stop_requested = pipeline.stop_requested
                existing.started_at = pipeline.started_at
                existing.completed_at = pipeline.completed_at
            else:
                db.add(_model_from_pipeline(pipeline, logs))
            await db.commit()

    async def delete(self, pipeline_id: str) -> None:
        async with await self._get_session() as db:
            model = await db.get(PipelineModel, pipeline_id)
            if model:
                await db.delete(model)
                await db.commit()

    async def delete_by_project(self, project_id: str) -> None:
        async with await self._get_session() as db:
            result = await db.execute(
                select(PipelineModel).where(PipelineModel.project_id == project_id)
            )
            for model in result.scalars().all():
                await db.delete(model)
            await db.commit()


def _model_from_pipeline(pipeline: Pipeline, logs: List[Dict] = None) -> PipelineModel:
    return PipelineModel(
        id=pipeline.id,
        project_id=pipeline.project_id,
        name=pipeline.name,
        status=pipeline.status.value,
        current_stage=pipeline.current_stage.value,
        progress=pipeline.progress,
        agents=pipeline.agents,
        task_ids=pipeline.task_ids,
        context=pipeline.context,
        logs=logs if logs is not None else pipeline.logs,
        team_config=getattr(pipeline, 'team_config', {}),
        agent_roles=getattr(pipeline, 'agent_roles', {}),
        stages=getattr(pipeline, 'stages', []),
        paused=pipeline.paused,
        stop_requested=pipeline.stop_requested,
        created_at=pipeline.created_at,
        started_at=pipeline.started_at,
        completed_at=pipeline.completed_at,
    )


def _pipeline_from_model(model: PipelineModel) -> Pipeline:
    pipeline = Pipeline()
    pipeline.id = model.id
    pipeline.project_id = model.project_id
    pipeline.name = model.name
    pipeline.status = PipelineStatus(model.status)
    pipeline.current_stage = PipelineStage(model.current_stage)
    pipeline.progress = model.progress
    pipeline.agents = model.agents or []
    pipeline.task_ids = model.task_ids or []
    pipeline.context = model.context or {}
    pipeline.logs = model.logs or []
    pipeline.team_config = model.team_config or {}
    pipeline.agent_roles = model.agent_roles or {}
    pipeline.stages = model.stages or []
    pipeline.paused = model.paused or False
    pipeline.stop_requested = model.stop_requested or False
    pipeline.created_at = model.created_at
    pipeline.started_at = model.started_at
    pipeline.completed_at = model.completed_at
    return pipeline


pipeline_persistence = PipelinePersistenceService()
