from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.agent.agent_executor import agent_executor
from app.services.collaboration.task_board import task_board
from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator
from app.services.execution.checkpoint_manager import checkpoint_manager
from app.services.execution.task_persistence_service import task_persistence_service
from app.services.execution.stuck_detector import stuck_detector

router = APIRouter(prefix="/api/execution", tags=["执行管理"])


@router.get("/tasks/{task_id}/status")
async def get_task_execution_status(task_id: str):
    """获取任务的详细执行状态（步骤级进度）"""
    status = agent_executor.get_execution_status(task_id)
    if not status:
        db_exec = await task_persistence_service.load_execution(task_id)
        if db_exec:
            return {
                "task_id": task_id,
                "agent_id": db_exec["agent_id"],
                "status": db_exec["status"],
                "current_step": db_exec["current_step_index"],
                "total_steps": db_exec["total_steps"],
                "last_heartbeat": db_exec["last_heartbeat"].isoformat() if db_exec["last_heartbeat"] else None,
                "accumulated_result": db_exec.get("accumulated_result"),
            }
        raise HTTPException(status_code=404, detail="Task execution not found")

    task = task_board.get_task(task_id)
    return {
        **status,
        "accumulated_result": task.accumulated_result if task else None,
    }


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str, from_checkpoint: bool = Query(default=True)):
    """重试失败的任务，可选择从检查点恢复"""
    if from_checkpoint:
        checkpoint = await checkpoint_manager.load_checkpoint(task_id)
        if checkpoint:
            success = await agent_executor.resume_execution(task_id)
        else:
            success = await agent_executor.resume_execution(task_id)
    else:
        await task_persistence_service.delete_execution(task_id)
        success = await agent_executor.resume_execution(task_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to retry task")
    return {"status": "retrying", "from_checkpoint": from_checkpoint}


@router.get("/stuck")
async def get_stuck_tasks(threshold_seconds: int = Query(default=120)):
    """列出所有疑似卡死的任务"""
    stuck = await stuck_detector.check_stuck_tasks()
    return {"stuck_tasks": stuck, "count": len(stuck)}


@router.get("/heartbeat/{task_id}")
async def get_task_heartbeat(task_id: str):
    """获取任务的心跳信息"""
    status = agent_executor.get_execution_status(task_id)
    if not status:
        db_exec = await task_persistence_service.load_execution(task_id)
        if db_exec:
            return {
                "task_id": task_id,
                "last_heartbeat": db_exec["last_heartbeat"].isoformat() if db_exec["last_heartbeat"] else None,
                "current_step": db_exec["current_step_index"],
                "total_steps": db_exec["total_steps"],
                "status": db_exec["status"],
            }
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "last_heartbeat": status.get("last_heartbeat"),
        "current_step": status.get("current_step", 0),
        "total_steps": status.get("total_steps", 1),
        "status": status.get("status"),
    }


@router.get("/tasks/{task_id}/checkpoints")
async def list_checkpoints(task_id: str):
    """列出任务的所有检查点"""
    checkpoints = await checkpoint_manager.list_checkpoints(task_id)
    return {"task_id": task_id, "checkpoints": checkpoints, "count": len(checkpoints)}


@router.post("/tasks/{task_id}/checkpoints/{checkpoint_id}/restore")
async def restore_checkpoint(task_id: str, checkpoint_id: str):
    """从指定检查点恢复执行"""
    checkpoints = await checkpoint_manager.list_checkpoints(task_id)
    target = None
    for cp in checkpoints:
        if cp["id"] == checkpoint_id:
            target = cp
            break

    if not target:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    resume_context, _ = checkpoint_manager.build_resume_context(target)
    return {"status": "restored", "checkpoint_id": checkpoint_id, "resume_context": resume_context}


@router.get("/monitor/status")
async def get_monitor_status():
    """获取卡死检测器的运行状态"""
    return {
        "monitoring": stuck_detector.is_running,
    }
