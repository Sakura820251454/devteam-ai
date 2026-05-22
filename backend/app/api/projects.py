from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.collaboration.project_service import project_service, ProjectPhase
from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator, PipelineStage


router = APIRouter(prefix="/api/projects", tags=["项目管理"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    requirements: str = ""
    created_by: str = "user"
    team_config: dict = Field(default_factory=dict)


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    status: Optional[str] = None
    current_phase: Optional[str] = None


class TaskBreakdownRequest(BaseModel):
    project_id: str
    requirements: str


class CreatePipelineRequest(BaseModel):
    project_id: str
    name: str
    agent_ids: List[str]


class InterveneRequest(BaseModel):
    pipeline_id: str
    message: str
    agent_id: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    current_phase: str
    requirements: str
    created_at: str
    updated_at: str


@router.post("/", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest):
    project = await project_service.create_project(
        name=request.name,
        description=request.description,
        requirements=request.requirements,
        created_by=request.created_by,
        team_config=request.team_config
    )
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status.value,
        current_phase=project.current_phase.value,
        requirements=project.requirements,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status.value,
        current_phase=project.current_phase.value,
        requirements=project.requirements,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, request: UpdateProjectRequest):
    from app.services.collaboration.project_service import ProjectStatus

    status = ProjectStatus(request.status) if request.status else None
    phase = ProjectPhase(request.current_phase) if request.current_phase else None

    project = await project_service.update_project(
        project_id=project_id,
        name=request.name,
        description=request.description,
        requirements=request.requirements,
        status=status,
        current_phase=phase
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status.value,
        current_phase=project.current_phase.value,
        requirements=project.requirements,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )


@router.post("/{project_id}/advance-phase", response_model=ProjectResponse)
async def advance_phase(project_id: str):
    project = await project_service.advance_phase(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status.value,
        current_phase=project.current_phase.value,
        requirements=project.requirements,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat()
    )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(status: Optional[str] = None):
    from app.services.collaboration.project_service import ProjectStatus

    project_status = ProjectStatus(status) if status else None
    projects = project_service.list_projects(project_status)

    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status.value,
            current_phase=p.current_phase.value,
            requirements=p.requirements,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat()
        )
        for p in projects
    ]


@router.delete("/{project_id}")
async def delete_project(project_id: str, cascade: bool = True):
    success = await project_service.delete_project(project_id, cascade=cascade)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "ok"}


@router.get("/{project_id}/summary")
async def get_project_summary(project_id: str):
    summary = project_service.get_project_summary(project_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Project not found")
    return summary


@router.post("/{project_id}/task-breakdown")
async def set_task_breakdown(project_id: str, request: TaskBreakdownRequest):
    project_service.set_task_breakdown_prompt(project_id, request.requirements)
    return {"status": "ok", "project_id": project_id}


@router.post("/{project_id}/tasks")
async def create_tasks_from_requirements(project_id: str):
    from app.models.task import Priority as TaskPriority, TaskStatus as TS
    from app.services.collaboration.task_board import task_board

    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    requirements = project.requirements or "Default development task"

    tasks_data = [
        {"title": f"开发: {requirements[:50]}", "description": requirements, "priority": TaskPriority.HIGH},
        {"title": f"测试: {requirements[:50]}", "description": requirements, "priority": TaskPriority.MEDIUM},
        {"title": f"部署: {requirements[:50]}", "description": requirements, "priority": TaskPriority.MEDIUM},
    ]

    created_tasks = []
    for task_data in tasks_data:
        task = await task_board.create_task(
            project_id=project_id,
            title=task_data["title"],
            description=task_data["description"],
            priority=task_data["priority"],
            created_by="system",
            tags=["auto-generated"]
        )
        created_tasks.append({
            "id": task.id,
            "title": task.title,
            "status": task.status.value
        })

    return {"project_id": project_id, "tasks": created_tasks}
