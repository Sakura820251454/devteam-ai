"""
安全与审计 API
- 权限查询/管理
- Kill Switch 控制
- 断路器状态
- 审计日志查询
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.security.guard import (
    security_guard,
    OperationType,
    EmergencyStopReason,
)
from app.services.security.audit import audit_logger, AuditAction

router = APIRouter(prefix="/api/security", tags=["安全与审计"])


# ==================== 权限 ====================

class GrantPermissionRequest(BaseModel):
    agent_id: str
    operations: List[str]


@router.get("/permissions/{agent_id}")
async def get_agent_permissions(agent_id: str):
    """获取 Agent 权限列表"""
    perms = security_guard.get_agent_permissions(agent_id)
    return {"agent_id": agent_id, "permissions": perms}


@router.post("/permissions/grant")
async def grant_permissions(request: GrantPermissionRequest):
    """授予 Agent 操作权限"""
    try:
        ops = [OperationType(op) for op in request.operations]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    security_guard.grant_permission(request.agent_id, ops)
    return {"agent_id": request.agent_id, "granted": request.operations}


@router.post("/permissions/revoke")
async def revoke_permission(agent_id: str, operation: str):
    """撤销 Agent 特定权限"""
    try:
        op = OperationType(operation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    security_guard.revoke_permission(agent_id, op)
    return {"agent_id": agent_id, "revoked": operation}


@router.post("/permissions/default/{agent_id}")
async def set_default_permissions(agent_id: str, agent_type: str = Query(...)):
    """根据 Agent 类型设置默认权限"""
    security_guard.set_default_permissions(agent_id, agent_type)
    perms = security_guard.get_agent_permissions(agent_id)
    return {"agent_id": agent_id, "agent_type": agent_type, "permissions": perms}


# ==================== 操作检查 ====================

@router.get("/check")
async def check_operation(
    operation: str,
    agent_id: str = "system"
):
    """检查操作是否允许执行"""
    try:
        op = OperationType(operation)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid operation: {operation}")

    result = security_guard.check_and_require_approval(op, agent_id)
    return result


@router.get("/risk-levels")
async def get_risk_levels():
    """获取所有操作的风险级别"""
    from app.services.security.guard import OPERATION_RISK_MAP
    return {
        "levels": {
            op.value: level.value
            for op, level in OPERATION_RISK_MAP.items()
        }
    }


# ==================== Kill Switch ====================

class EmergencyStopRequest(BaseModel):
    triggered_by: str
    reason: str = "human_triggered"
    message: str = ""


class EmergencyResetRequest(BaseModel):
    triggered_by: str


@router.post("/emergency/stop")
async def emergency_stop(request: EmergencyStopRequest):
    """全局紧急停止"""
    try:
        reason = EmergencyStopReason(request.reason)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid reason: {request.reason}")

    state = await security_guard.emergency_stop(
        triggered_by=request.triggered_by,
        reason=reason,
        message=request.message
    )

    # 审计日志
    from app.services.security.audit import audit_logger, AuditAction
    audit_logger.log(
        action=AuditAction.EMERGENCY_STOP,
        actor=request.triggered_by,
        detail=request.message or f"紧急停止: {reason.value}",
    )

    return state


@router.post("/emergency/reset")
async def emergency_reset(request: EmergencyResetRequest):
    """解除紧急状态"""
    state = await security_guard.emergency_reset(request.triggered_by)

    from app.services.security.audit import audit_logger, AuditAction
    audit_logger.log(
        action=AuditAction.EMERGENCY_RESET,
        actor=request.triggered_by,
        detail="紧急状态已解除",
    )

    return state


@router.get("/emergency/state")
async def get_emergency_state():
    """获取当前紧急状态"""
    return security_guard.emergency_state


# ==================== 断路器 ====================

@router.get("/circuit-breaker/{agent_id}")
async def get_agent_error_stats(agent_id: str):
    """获取 Agent 的断路器统计"""
    stats = security_guard.get_agent_error_stats(agent_id)
    return {"agent_id": agent_id, "stats": stats}


@router.post("/circuit-breaker/{agent_id}/reset")
async def reset_circuit_breaker(agent_id: str):
    """重置 Agent 的断路器"""
    security_guard.reset_circuit_breaker(agent_id)

    from app.services.security.audit import audit_logger, AuditAction
    audit_logger.log(
        action=AuditAction.CIRCUIT_BREAKER_TRIGGERED,
        actor="api",
        agent_id=agent_id,
        detail="断路器已重置",
    )

    return {"agent_id": agent_id, "circuit_breaker": "reset"}


# ==================== 审计日志 ====================

@router.get("/audit")
async def query_audit_logs(
    action: Optional[str] = None,
    actor: Optional[str] = None,
    agent_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """查询审计日志"""
    audit_action = None
    if action:
        try:
            audit_action = AuditAction(action)
        except ValueError:
            pass

    results = audit_logger.query(
        action=audit_action,
        actor=actor,
        agent_id=agent_id,
        risk_level=risk_level,
        outcome=outcome,
        limit=limit,
        offset=offset
    )
    return {"total": len(results), "entries": results}


@router.get("/audit/critical")
async def get_critical_events(limit: int = 50):
    """获取高危/严重事件"""
    events = audit_logger.get_critical_events(limit)
    return {"total": len(events), "events": events}


@router.get("/audit/summary")
async def get_audit_summary():
    """获取审计摘要统计"""
    return audit_logger.get_summary()


@router.get("/audit/verify")
async def verify_audit_integrity():
    """验证审计日志完整性（哈希链校验）"""
    return audit_logger.verify_integrity()
