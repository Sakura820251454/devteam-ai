from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.collaboration.task_board import task_board
from app.models.task import Task, TaskStatus, Priority, TaskHistory


router = APIRouter(prefix="/api/tasks", tags=["任务看板"])


class CreateTaskRequest(BaseModel):
    project_id: str = ""
    title: str
    description: str = ""
    priority: Priority = Priority.MEDIUM
    assigned_agents: List[str] = Field(default_factory=list)
    created_by: str = "system"
    tags: List[str] = Field(default_factory=list)


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    tags: Optional[List[str]] = None


class AssignAgentsRequest(BaseModel):
    agent_ids: List[str]


class ChangeStatusRequest(BaseModel):
    status: TaskStatus
    changed_by: str = "system"


class AddCommentRequest(BaseModel):
    comment: str
    author: str = "system"


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    project_id: str = ""
    status: TaskStatus
    priority: Priority
    risk_level: str = "low"
    assigned_agents: List[str]
    collaborated_agents: List[str]
    dependencies: List[str]
    linked_documents: List[str]
    created_by: str
    tags: List[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    approval_required: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    history: List[TaskHistory]


def task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        project_id=getattr(task, 'project_id', ''),
        status=task.status,
        priority=task.priority,
        risk_level=getattr(task, 'risk_level', 'low') or 'low',
        assigned_agents=task.assigned_agents,
        collaborated_agents=task.collaborated_agents,
        dependencies=task.dependencies,
        linked_documents=task.linked_documents,
        created_by=task.created_by,
        tags=task.tags,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        approval_required=getattr(task, 'approval_required', False) or False,
        approved_by=getattr(task, 'approved_by', None) or None,
        approved_at=task.approved_at.isoformat() if getattr(task, 'approved_at', None) else None,
        history=task.history
    )


@router.post("/", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    task = await task_board.create_task(
        project_id=request.project_id,
        title=request.title,
        description=request.description,
        priority=request.priority,
        assigned_agents=request.assigned_agents,
        created_by=request.created_by,
        tags=request.tags
    )
    return task_to_response(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = task_board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, request: UpdateTaskRequest):
    task = await task_board.update_task(
        task_id=task_id,
        title=request.title,
        description=request.description,
        priority=request.priority,
        tags=request.tags
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)


@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_agents(task_id: str, request: AssignAgentsRequest):
    task = await task_board.assign_agents(task_id, request.agent_ids)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)


@router.post("/{task_id}/status", response_model=TaskResponse)
async def change_status(task_id: str, request: ChangeStatusRequest):
    try:
        task = await task_board.change_status(task_id, request.status, request.changed_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)


@router.post("/{task_id}/comment", response_model=TaskResponse)
async def add_comment(task_id: str, request: AddCommentRequest):
    task = await task_board.add_comment(task_id, request.comment, request.author)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    success = await task_board.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok"}


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[Priority] = None,
    assigned_agent: Optional[str] = None,
    project_id: Optional[str] = None,
    tags: Optional[str] = None,
    created_by: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    tags_list = tags.split(",") if tags else None
    tasks = task_board.list_tasks(
        project_id=project_id,
        status=status,
        priority=priority,
        assigned_agent=assigned_agent,
        tags=tags_list,
        created_by=created_by,
        limit=limit,
        offset=offset
    )
    return [task_to_response(t) for t in tasks]


@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(status: TaskStatus, project_id: Optional[str] = None):
    tasks = task_board.get_tasks_by_status(status, project_id=project_id)
    return [task_to_response(t) for t in tasks]


@router.get("/agent/{agent_id}", response_model=List[TaskResponse])
async def get_tasks_by_agent(agent_id: str, project_id: Optional[str] = None):
    tasks = task_board.get_tasks_by_agent(agent_id, project_id=project_id)
    return [task_to_response(t) for t in tasks]


@router.get("/board/all", response_model=dict)
async def get_board(project_id: Optional[str] = None):
    board = task_board.get_tasks_by_board(project_id=project_id)
    return {
        "total": task_board.get_task_count(project_id=project_id),
        "columns": {
            status.value: [task_to_response(t) for t in tasks]
            for status, tasks in board.items()
        }
    }


@router.get("/count/{status}")
async def get_task_count(status: Optional[TaskStatus] = None, project_id: Optional[str] = None):
    count = task_board.get_task_count(status, project_id=project_id)
    return {"status": status.value if status else "all", "count": count}


@router.get("/search/{query}", response_model=List[TaskResponse])
async def search_tasks(query: str, project_id: Optional[str] = None):
    tasks = task_board.search_tasks(query, project_id=project_id)
    return [task_to_response(t) for t in tasks]
