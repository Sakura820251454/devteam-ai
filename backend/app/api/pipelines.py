from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator, PipelineStage


router = APIRouter(prefix="/api/pipelines", tags=["流水线"])


class CreatePipelineRequest(BaseModel):
    project_id: str
    name: str
    agent_ids: List[str]


class InterveneRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None


@router.post("/")
async def create_pipeline(request: CreatePipelineRequest):
    pipeline = await pipeline_orchestrator.create_pipeline(
        project_id=request.project_id,
        name=request.name,
        agent_ids=request.agent_ids
    )
    return {
        "id": pipeline.id,
        "project_id": pipeline.project_id,
        "name": pipeline.name,
        "status": pipeline.status.value
    }


@router.get("/")
async def list_pipelines():
    pipelines = pipeline_orchestrator.list_pipelines()
    return {"pipelines": pipelines}


@router.get("/active")
async def get_active_pipeline():
    pipeline = pipeline_orchestrator.get_active_pipeline()
    if not pipeline:
        return {"pipeline": None, "message": "No active pipeline"}
    return {"pipeline": pipeline}


@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    pipeline = pipeline_orchestrator.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.post("/{pipeline_id}/start")
async def start_pipeline(pipeline_id: str):
    success = await pipeline_orchestrator.start_pipeline(pipeline_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start pipeline")
    return {"status": "started", "pipeline_id": pipeline_id}


@router.post("/{pipeline_id}/pause")
async def pause_pipeline(pipeline_id: str):
    success = await pipeline_orchestrator.pause_pipeline(pipeline_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pause pipeline")
    return {"status": "paused", "pipeline_id": pipeline_id}


@router.post("/{pipeline_id}/resume")
async def resume_pipeline(pipeline_id: str):
    success = await pipeline_orchestrator.resume_pipeline(pipeline_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume pipeline")
    return {"status": "resumed", "pipeline_id": pipeline_id}


@router.post("/{pipeline_id}/stop")
async def stop_pipeline(pipeline_id: str):
    success = await pipeline_orchestrator.stop_pipeline(pipeline_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to stop pipeline")
    return {"status": "stopped", "pipeline_id": pipeline_id}


@router.post("/{pipeline_id}/intervene")
async def intervene(pipeline_id: str, request: InterveneRequest):
    await pipeline_orchestrator.intervene(
        pipeline_id=pipeline_id,
        message=request.message,
        agent_id=request.agent_id
    )
    return {"status": "intervention_sent"}


@router.get("/{pipeline_id}/logs")
async def get_pipeline_logs(pipeline_id: str, limit: int = 50):
    pipeline = pipeline_orchestrator.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"logs": pipeline.get("logs", [])[-limit:]}


@router.get("/{pipeline_id}/status")
async def get_pipeline_status(pipeline_id: str):
    from app.services.agent.agent_executor import agent_executor

    pipeline = pipeline_orchestrator.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    running_tasks = agent_executor.get_running_tasks()

    return {
        "pipeline_id": pipeline_id,
        "status": pipeline.get("status"),
        "current_stage": pipeline.get("current_stage"),
        "progress": pipeline.get("progress"),
        "running_tasks": running_tasks,
        "is_paused": agent_executor.is_global_paused()
    }


@router.get("/interventions/queue")
async def get_intervention_queue():
    queue = pipeline_orchestrator.get_intervention_queue()
    return {"queue": queue}
