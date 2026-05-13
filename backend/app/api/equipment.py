"""
装备模块API - Phase 5

提供工具注册、查询、装备管理等REST接口
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.equipment.equipment_service import (
    equipment_service,
    ToolMetadata,
    ToolType,
    ResourceCost,
)

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("/tools")
async def get_all_tools(
    tool_type: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
):
    """获取工具列表"""
    tools = equipment_service.tool_registry.find_all()
    
    if tool_type:
        try:
            t_type = ToolType(tool_type)
            tools = [t for t in tools if t.type == t_type]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tool type: {tool_type}")
    
    if capability:
        tools = equipment_service.tool_registry.find_by_capability(capability)
    
    if task_type:
        tools = equipment_service.tool_registry.find_by_task(task_type)
    
    return {
        "tools": [_tool_to_dict(t) for t in tools],
        "count": len(tools),
    }


@router.get("/tools/{tool_id}")
async def get_tool(tool_id: str):
    """获取工具详情"""
    tool = equipment_service.tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    return _tool_to_dict(tool)


@router.post("/tools")
async def register_tool(tool_data: Dict[str, Any]):
    """注册新工具"""
    try:
        tool = ToolMetadata(
            id=tool_data.get("id", f"tool_{datetime.now().timestamp()}"),
            name=tool_data["name"],
            type=ToolType(tool_data["type"]),
            version=tool_data.get("version", "1.0"),
            description=tool_data.get("description", ""),
            capabilities=tool_data.get("capabilities", []),
            suitable_tasks=tool_data.get("suitable_tasks", []),
            resource_cost=ResourceCost(
                tokens=tool_data.get("tokens", 0),
                memory_mb=tool_data.get("memory_mb", 0),
                seconds=tool_data.get("seconds", 0),
            ),
            depends_on=tool_data.get("depends_on", []),
            excludes=tool_data.get("excludes", []),
        )
        
        equipment_service.register_tool(tool)
        
        return {
            "message": "Tool registered successfully",
            "tool": _tool_to_dict(tool),
        }
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tools/{tool_id}")
async def unregister_tool(tool_id: str):
    """注销工具"""
    success = equipment_service.tool_registry.unregister(tool_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    return {"message": "Tool unregistered successfully"}


@router.post("/agent/{agent_id}/analyze")
async def analyze_task(agent_id: str, task_description: str):
    """分析任务需求"""
    requirements = equipment_service.task_analyzer.analyze(task_description)
    
    return {
        "agent_id": agent_id,
        "task_description": task_description,
        "required_tools": [_tool_to_dict(t) for t in requirements.required_tools],
        "optional_tools": [_tool_to_dict(t) for t in requirements.optional_tools],
        "priority_estimate": requirements.priority_estimate,
        "resource_estimate": {
            "tokens": requirements.resource_estimate.tokens,
            "memory_mb": requirements.resource_estimate.memory_mb,
            "seconds": requirements.resource_estimate.seconds,
        },
        "confidence": requirements.confidence,
    }


@router.post("/agent/{agent_id}/equip")
async def equip_tools(agent_id: str, task_description: str):
    """分析任务并自动装备工具"""
    equipped_ids, confidence = equipment_service.analyze_and_equip(agent_id, task_description)
    
    context = equipment_service.get_agent_equipment(agent_id)
    
    return {
        "agent_id": agent_id,
        "task_description": task_description,
        "equipped_tools": equipped_ids,
        "all_equipped": [_tool_to_dict(t) for t in context.equipped_tools] if context else [],
        "confidence": confidence,
        "message": f"Successfully equipped {len(equipped_ids)} tools",
    }


@router.get("/agent/{agent_id}/equipment")
async def get_agent_equipment(agent_id: str):
    """获取Agent装备状态"""
    context = equipment_service.get_agent_equipment(agent_id)
    
    if not context:
        return {
            "agent_id": agent_id,
            "equipped_tools": [],
            "capabilities": [],
            "message": "No equipment context found",
        }
    
    return {
        "agent_id": agent_id,
        "equipped_tools": [_tool_to_dict(t) for t in context.equipped_tools],
        "capabilities": context.get_equipped_capabilities(),
        "last_equipped_at": context.last_equipped_at,
    }


@router.post("/agent/{agent_id}/unequip/{tool_id}")
async def unequip_tool(agent_id: str, tool_id: str):
    """卸载指定工具"""
    context = equipment_service.get_agent_equipment(agent_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    success = context.unequip(tool_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Tool not equipped: {tool_id}")
    
    return {"message": f"Tool {tool_id} unequipped successfully"}


@router.post("/agent/{agent_id}/unequip-all")
async def unequip_all_tools(agent_id: str):
    """卸载所有工具"""
    context = equipment_service.get_agent_equipment(agent_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    context.unequip_all()
    
    return {"message": "All tools unequipped successfully"}


@router.get("/stats")
async def get_equipment_stats():
    """获取装备系统统计"""
    stats = equipment_service.tool_registry.get_tool_stats() if hasattr(equipment_service.tool_registry, 'get_tool_stats') else {}
    
    all_tools = equipment_service.tool_registry.find_all()
    
    return {
        "total_tools": len(all_tools),
        "by_type": {t.value: len([x for x in all_tools if x.type == t]) for t in ToolType},
        "total_usage": sum(t.usage_count for t in all_tools),
        "avg_success_rate": sum(t.success_rate for t in all_tools) / len(all_tools) if all_tools else 0,
    }


@router.post("/tools/{tool_id}/usage")
async def update_tool_usage(
    tool_id: str,
    agent_id: str,
    success: bool = Query(True),
    execution_time: float = Query(0.0),
):
    """更新工具使用统计"""
    equipment_service.update_tool_usage(agent_id, tool_id, success, execution_time)
    
    tool = equipment_service.tool_registry.get(tool_id)
    
    return {
        "message": "Usage stats updated",
        "tool": _tool_to_dict(tool) if tool else None,
    }


def _tool_to_dict(tool: ToolMetadata) -> Dict[str, Any]:
    """工具对象转字典"""
    return {
        "id": tool.id,
        "name": tool.name,
        "type": tool.type.value,
        "version": tool.version,
        "description": tool.description,
        "capabilities": tool.capabilities,
        "suitable_tasks": tool.suitable_tasks,
        "resource_cost": {
            "tokens": tool.resource_cost.tokens,
            "memory_mb": tool.resource_cost.memory_mb,
            "seconds": tool.resource_cost.seconds,
        },
        "depends_on": tool.depends_on,
        "excludes": tool.excludes,
        "usage_count": tool.usage_count,
        "success_rate": tool.success_rate,
        "avg_execution_time": tool.avg_execution_time,
        "created_at": tool.created_at,
        "updated_at": tool.updated_at,
    }
