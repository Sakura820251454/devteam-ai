from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.services.project.workspace_manager import workspace_manager

router = APIRouter(prefix="/api/workspaces", tags=["工作区管理"])


class CreateWorkspaceRequest(BaseModel):
    project_id: str
    name: str
    description: str = ""
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    stages: List[Dict[str, Any]] = Field(default_factory=list)
    team_config: Optional[Dict[str, Any]] = None
    template: Optional[Dict[str, Any]] = None


class AddArtifactRequest(BaseModel):
    stage_key: str
    name: str
    content: str = ""


class AddLogRequest(BaseModel):
    level: str = "info"
    source: str = "system"
    message: str


@router.post("/")
def create_workspace(request: CreateWorkspaceRequest):
    data = workspace_manager.create_workspace(
        project_id=request.project_id,
        name=request.name,
        description=request.description,
        agents=request.agents,
        stages=request.stages,
        team_config=request.team_config,
        template=request.template,
    )
    return {
        "workspace": data,
        "workspace_path": str(
            workspace_manager._workspace_dir(request.project_id)
        ),
    }


@router.get("/")
def list_workspaces():
    return {"workspaces": workspace_manager.list_workspaces()}


@router.get("/{project_id}")
def get_workspace(project_id: str):
    ws = workspace_manager.get_workspace(project_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.post("/{project_id}/artifacts")
def add_artifact(project_id: str, request: AddArtifactRequest):
    path = workspace_manager.add_artifact(
        project_id=project_id,
        stage_key=request.stage_key,
        name=request.name,
        content=request.content,
    )
    if path is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"path": path, "stage": request.stage_key, "name": request.name}


@router.get("/{project_id}/files")
def list_files(project_id: str, subdir: str = Query("")):
    exists = workspace_manager.get_workspace(project_id)
    if not exists:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"files": workspace_manager.list_files(project_id, subdir)}


@router.get("/{project_id}/files/{file_path:path}")
def read_file(project_id: str, file_path: str):
    content = workspace_manager.read_file(project_id, file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": file_path, "content": content}


@router.post("/{project_id}/logs")
def add_log(project_id: str, request: AddLogRequest):
    workspace_manager.add_log(
        project_id=project_id,
        level=request.level,
        source=request.source,
        message=request.message,
    )
    return {"status": "ok"}


@router.patch("/{project_id}/status")
def update_status(
    project_id: str,
    status: str = Query(...),
    current_stage: str = Query(""),
):
    ok = workspace_manager.update_status(project_id, status, current_stage)
    if not ok:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "ok"}


@router.delete("/{project_id}")
def delete_workspace(project_id: str):
    ok = workspace_manager.delete_workspace(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "ok"}


# ========== Artifact API ==========

class GetArtifactStatusRequest(BaseModel):
    stages: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/{project_id}/artifacts/status")
def get_artifact_status(project_id: str, request: GetArtifactStatusRequest):
    """获取各阶段的产出物状态"""
    return workspace_manager.get_artifact_status(project_id, request.stages)


@router.get("/{project_id}/artifacts/prerequisites")
def get_prerequisite_artifacts(
    project_id: str,
    current_stage: str = Query(...),
    stage_order: str = Query(""),
):
    """获取前置阶段的产出物内容"""
    order = [s.strip() for s in stage_order.split(",") if s.strip()]
    return workspace_manager.get_prerequisite_artifacts(project_id, current_stage, order)
