import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models.core_db import ProjectModel
from app.services.collaboration.project_service import Project, ProjectStatus, ProjectPhase


class ProjectPersistenceService:
    """项目持久化服务 — CRUD for ProjectModel"""

    def __init__(self):
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    def initialize(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def _get_session(self) -> AsyncSession:
        if not self._session_maker:
            raise RuntimeError("ProjectPersistenceService not initialized")
        return self._session_maker()

    async def load_all(self) -> Dict[str, Project]:
        async with await self._get_session() as db:
            result = await db.execute(select(ProjectModel))
            models = result.scalars().all()
            return {m.id: _project_from_model(m) for m in models}

    async def save(self, project: Project) -> None:
        async with await self._get_session() as db:
            existing = await db.get(ProjectModel, project.id)
            if existing:
                existing.name = project.name
                existing.description = project.description
                existing.status = project.status.value
                existing.current_phase = project.current_phase.value
                existing.requirements = project.requirements
                existing.team_config = project.team_config
                existing.settings = project.settings
                existing.updated_at = datetime.now()
            else:
                db.add(_model_from_project(project))
            await db.commit()

    async def delete(self, project_id: str) -> None:
        async with await self._get_session() as db:
            model = await db.get(ProjectModel, project_id)
            if model:
                await db.delete(model)
                await db.commit()


def _model_from_project(project: Project) -> ProjectModel:
    return ProjectModel(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status.value,
        current_phase=project.current_phase.value,
        requirements=project.requirements,
        team_config=project.team_config,
        settings=project.settings,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _project_from_model(model: ProjectModel) -> Project:
    return Project(
        id=model.id,
        name=model.name,
        description=model.description or "",
        status=ProjectStatus(model.status),
        current_phase=ProjectPhase(model.current_phase),
        requirements=model.requirements or "",
        team_config=model.team_config or {},
        settings=model.settings or {},
        created_by=model.created_by or "user",
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


project_persistence = ProjectPersistenceService()
