from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator, PipelineStage
from app.services.collaboration.pipeline_templates import (
    get_all_templates, get_template_by_id, get_templates_by_category,
    suggest_stage_adjustments, apply_stage_adjustments,
)


router = APIRouter(prefix="/api/pipelines", tags=["流水线"])


class CreatePipelineRequest(BaseModel):
    project_id: str
    name: str
    agent_ids: List[str]
    team_config: Optional[dict] = None


class InterveneRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None


# ========== Collection routes ==========

@router.post("/")
async def create_pipeline(request: CreatePipelineRequest):
    try:
        pipeline = await pipeline_orchestrator.create_pipeline(
            project_id=request.project_id,
            name=request.name,
            agent_ids=request.agent_ids,
            team_config=request.team_config or {},
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {
        "id": pipeline.id,
        "project_id": pipeline.project_id,
        "name": pipeline.name,
        "status": pipeline.status.value
    }


@router.get("/")
async def list_pipelines(project_id: Optional[str] = None):
    if project_id:
        pipelines = pipeline_orchestrator.list_pipelines_by_project(project_id)
    else:
        pipelines = pipeline_orchestrator.list_pipelines()
    return {"pipelines": pipelines}


# ========== Static routes (MUST be before /{pipeline_id}) ==========

@router.get("/active")
async def get_active_pipeline(project_id: Optional[str] = None):
    pipeline = pipeline_orchestrator.get_active_pipeline(project_id=project_id)
    if not pipeline:
        return {"pipeline": None, "message": "No active pipeline"}
    return {"pipeline": pipeline}


@router.get("/interventions/queue")
async def get_intervention_queue():
    queue = pipeline_orchestrator.get_intervention_queue()
    return {"queue": queue}


# ========== Pipeline Template API ==========

@router.get("/templates")
async def list_pipeline_templates(category: str = None):
    if category:
        templates = get_templates_by_category(category)
    else:
        templates = get_all_templates()
    return {
        "templates": [t.to_dict() for t in templates],
        "categories": [
            {"key": "simple", "label": "简单任务"},
            {"key": "development", "label": "开发项目"},
            {"key": "design", "label": "方案设计"},
            {"key": "complex", "label": "复杂系统"},
        ],
    }


@router.get("/templates/{template_id}")
async def get_pipeline_template(template_id: str):
    template = get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    return template.to_dict()


class AdjustTemplateRequest(BaseModel):
    project_name: str
    project_description: str
    template_id: str


class StrategyRecommendRequest(BaseModel):
    project_name: str
    project_description: str
    requirements: str = ""
    agent_ids: List[str]
    template_id: Optional[str] = None


@router.post("/recommend-strategy")
async def recommend_strategy(request: StrategyRecommendRequest):
    from app.services.collaboration.strategy_recommender import strategy_recommender

    recommendation = await strategy_recommender.recommend(
        project_name=request.project_name,
        project_description=request.project_description,
        requirements=request.requirements,
        agent_ids=request.agent_ids,
        template_id=request.template_id,
    )
    return {
        "recommended_strategy": recommendation.recommended_strategy,
        "confidence": recommendation.confidence,
        "reasoning": recommendation.reasoning,
        "suggested_coordinator": recommendation.suggested_coordinator,
        "alternative_strategies": recommendation.alternative_strategies,
    }


@router.post("/templates/adjust")
async def adjust_pipeline_template(request: AdjustTemplateRequest):
    suggestions = await suggest_stage_adjustments(
        project_name=request.project_name,
        project_description=request.project_description,
        template_id=request.template_id,
    )
    return suggestions


class ApplyAdjustmentRequest(BaseModel):
    template_id: str
    adjustments: dict


@router.post("/templates/apply")
async def apply_pipeline_adjustment(request: ApplyAdjustmentRequest):
    stages = apply_stage_adjustments(request.template_id, request.adjustments)
    return {"stages": stages}


class UpdateStagesRequest(BaseModel):
    stages: list[dict]
    project_id: Optional[str] = None


@router.put("/{pipeline_id}/stages")
async def update_pipeline_stages(pipeline_id: str, request: UpdateStagesRequest):
    """Persist adjusted pipeline stages to DB and workspace."""
    from app.services.project.workspace_manager import workspace_manager

    project_id = await pipeline_orchestrator.update_pipeline_stages(
        pipeline_id, request.stages
    )

    effective_project_id = project_id or request.project_id
    if effective_project_id:
        try:
            workspace_manager.update_stages(effective_project_id, request.stages)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update workspace stages: {str(e)}",
            )

    return {"status": "ok", "stages": request.stages}


# ========== /{pipeline_id} routes (MUST be after all static routes) ==========

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


@router.post("/{pipeline_id}/close")
async def close_pipeline(pipeline_id: str):
    """关闭流水线：取消执行、保存状态为 PAUSED，用户可在之后恢复。"""
    success = await pipeline_orchestrator.close_pipeline(pipeline_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to close pipeline")
    return {"status": "closed", "pipeline_id": pipeline_id}


@router.post("/{pipeline_id}/resume-from-close")
async def resume_from_close(pipeline_id: str):
    """从关闭状态恢复流水线执行。"""
    success = await pipeline_orchestrator.resume_from_close(pipeline_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume pipeline from closed state")
    return {"status": "resumed", "pipeline_id": pipeline_id}


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

    try:
        running_tasks = agent_executor.get_running_tasks()
    except Exception:
        running_tasks = []

    try:
        is_paused = agent_executor.is_project_paused(pipeline.get("project_id", ""))
    except Exception:
        is_paused = False

    return {
        "pipeline_id": pipeline_id,
        "status": pipeline.get("status"),
        "current_stage": pipeline.get("current_stage"),
        "progress": pipeline.get("progress"),
        "running_tasks": running_tasks,
        "is_paused": is_paused,
    }
