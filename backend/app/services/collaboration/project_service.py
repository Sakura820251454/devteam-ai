import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectPhase(str, Enum):
    REQUIREMENT = "requirement"
    DESIGN = "design"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING)
    current_phase: ProjectPhase = Field(default=ProjectPhase.REQUIREMENT)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "user"
    requirements: str = ""
    team_config: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)


class TaskBreakdownRequest(BaseModel):
    project_id: str
    requirements: str
    agent_capabilities: Dict[str, List[str]] = Field(default_factory=dict)


class BrokenDownTask(BaseModel):
    title: str
    description: str
    assigned_role: str
    priority: str = "medium"
    estimated_complexity: str = "medium"
    dependencies: List[str] = Field(default_factory=list)
    phase: ProjectPhase = ProjectPhase.DEVELOPMENT
    acceptance_criteria: List[str] = Field(default_factory=list)


class TaskBreakdownResult(BaseModel):
    project_id: str
    tasks: List[BrokenDownTask]
    summary: str = ""
    suggested_order: List[int] = Field(default_factory=list)


class ProjectService:
    def __init__(self):
        self._projects: Dict[str, Project] = {}
        self._task_breakdown_prompts: Dict[str, str] = {}
        self._db = None

    def initialize(self, db_service) -> None:
        self._db = db_service

    async def load_all(self) -> None:
        if self._db:
            self._projects = await self._db.load_all()

    async def create_project(
        self,
        name: str,
        description: str = "",
        requirements: str = "",
        created_by: str = "user",
        team_config: Dict[str, Any] = None
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            requirements=requirements,
            created_by=created_by,
            team_config=team_config or {}
        )
        self._projects[project.id] = project
        if self._db:
            await self._db.save(project)
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    async def update_project(
        self,
        project_id: str,
        name: str = None,
        description: str = None,
        requirements: str = None,
        status: str = None,
        current_phase: str = None
    ) -> Optional[Project]:
        project = self._projects.get(project_id)
        if not project:
            return None

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if requirements is not None:
            project.requirements = requirements
        if status is not None:
            project.status = ProjectStatus(status) if isinstance(status, str) else status
        if current_phase is not None:
            project.current_phase = ProjectPhase(current_phase) if isinstance(current_phase, str) else current_phase

        project.updated_at = datetime.now()
        if self._db:
            await self._db.save(project)
        return project

    def list_projects(self, status: ProjectStatus = None) -> List[Project]:
        projects = list(self._projects.values())
        if status:
            projects = [p for p in projects if p.status == status]
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    async def delete_project(self, project_id: str, cascade: bool = True) -> bool:
        if project_id not in self._projects:
            return False
        if cascade:
            await self._cleanup_project(project_id)
        del self._projects[project_id]
        if project_id in self._task_breakdown_prompts:
            del self._task_breakdown_prompts[project_id]
        if self._db:
            await self._db.delete(project_id)
        return True

    async def _cleanup_project(self, project_id: str) -> None:
        """级联清理项目相关资源"""
        from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator
        from app.services.collaboration.task_board import task_board
        from app.services.collaboration.message_bus import message_bus
        from app.services.collaboration.arbitrator import arbitrator
        from app.services.agent.agent_service import agent_service
        from app.services.agent.agent_executor import agent_executor
        from app.services.project.workspace_manager import workspace_manager

        # 停止项目 pipeline
        for pid in list(pipeline_orchestrator._active_pipelines.keys()):
            if pid == project_id:
                pipeline_id = pipeline_orchestrator._active_pipelines[pid]
                await pipeline_orchestrator.stop_pipeline(pipeline_id)

        # 释放 Agent
        agent_service.release_project_agents(project_id)

        # 清理任务
        await task_board.clear_project_tasks(project_id)

        # 清理消息
        message_bus.clear_project_history(project_id)
        message_bus.cleanup_project_channels(project_id)

        # 清理仲裁
        arbitrator.clear_project_issues(project_id)

        # 清理工作区
        try:
            workspace_manager.delete_workspace(project_id)
        except Exception:
            pass

    def get_project_summary(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取项目汇总信息"""
        project = self._projects.get(project_id)
        if not project:
            return None

        from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator
        from app.services.collaboration.task_board import task_board
        from app.services.agent.agent_service import agent_service

        pipelines = pipeline_orchestrator.list_pipelines_by_project(project_id)
        active_pipeline = pipeline_orchestrator.get_active_pipeline(project_id)
        task_count = task_board.get_task_count(project_id=project_id)
        agents = agent_service.get_project_agents(project_id)

        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status.value if hasattr(project.status, 'value') else project.status,
            "current_phase": project.current_phase.value if hasattr(project.current_phase, 'value') else project.current_phase,
            "created_at": project.created_at.isoformat() if hasattr(project.created_at, 'isoformat') else str(project.created_at),
            "updated_at": project.updated_at.isoformat() if hasattr(project.updated_at, 'isoformat') else str(project.updated_at),
            "pipeline_count": len(pipelines),
            "active_pipeline": active_pipeline,
            "task_count": task_count,
            "agent_count": len(agents),
            "agents": [{"id": a["id"], "name": a.get("name", ""), "type": a.get("type", "")} for a in agents],
        }

    async def advance_phase(self, project_id: str) -> Optional[Project]:
        project = self._projects.get(project_id)
        if not project:
            return None

        phase_order = [
            ProjectPhase.REQUIREMENT,
            ProjectPhase.DESIGN,
            ProjectPhase.DEVELOPMENT,
            ProjectPhase.TESTING,
            ProjectPhase.DEPLOYMENT
        ]

        try:
            current_idx = phase_order.index(project.current_phase)
            if current_idx < len(phase_order) - 1:
                project.current_phase = phase_order[current_idx + 1]
                project.updated_at = datetime.now()
                if self._db:
                    await self._db.save(project)
                return project
        except ValueError:
            pass

        return project

    def set_task_breakdown_prompt(self, project_id: str, prompt: str) -> None:
        self._task_breakdown_prompts[project_id] = prompt

    def get_task_breakdown_prompt(self, project_id: str) -> Optional[str]:
        return self._task_breakdown_prompts.get(project_id)


project_service = ProjectService()
