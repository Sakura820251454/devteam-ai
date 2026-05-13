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

    def create_project(
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
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def update_project(
        self,
        project_id: str,
        name: str = None,
        description: str = None,
        requirements: str = None,
        status: ProjectStatus = None,
        current_phase: ProjectPhase = None
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
            project.status = status
        if current_phase is not None:
            project.current_phase = current_phase

        project.updated_at = datetime.now()
        return project

    def list_projects(self, status: ProjectStatus = None) -> List[Project]:
        projects = list(self._projects.values())
        if status:
            projects = [p for p in projects if p.status == status]
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    def delete_project(self, project_id: str) -> bool:
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False

    def advance_phase(self, project_id: str) -> Optional[Project]:
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
                return project
        except ValueError:
            pass

        return project

    def set_task_breakdown_prompt(self, project_id: str, prompt: str) -> None:
        self._task_breakdown_prompts[project_id] = prompt

    def get_task_breakdown_prompt(self, project_id: str) -> Optional[str]:
        return self._task_breakdown_prompts.get(project_id)


project_service = ProjectService()
