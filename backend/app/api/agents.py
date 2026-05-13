"""
Agent 管理 API 路由
提供 Agent 模板和实例的管理接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.agent.agent_service import agent_service, AgentType

router = APIRouter(prefix="/api/agents", tags=["Agent管理"])


class CreateTemplateRequest(BaseModel):
    name: str
    type: str = "custom"
    description: str = ""
    avatar_color: str = "#6B7280"
    system_prompt: str
    capabilities: List[str] = []
    collaboration_style: str = ""
    speaking_tendency: str = ""
    tags: List[str] = []
    suitable_scenarios: List[str] = []


class CreateAgentRequest(BaseModel):
    template_id: str
    name: Optional[str] = None


class CreateAgentFromSoulRequest(BaseModel):
    soul_name: str
    name: Optional[str] = None


class CreateTeamRequest(BaseModel):
    name: str
    agent_ids: List[str]


@router.get("/templates")
def get_all_templates():
    """获取所有 Agent 模板"""
    return {
        "templates": agent_service.get_all_templates(),
        "total": len(agent_service.get_all_templates())
    }


@router.get("/templates/{template_id}")
def get_template(template_id: str):
    """获取指定模板"""
    template = agent_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("/templates/type/{agent_type}")
def get_templates_by_type(agent_type: str):
    """按类型获取模板"""
    try:
        templates = agent_service.get_templates_by_type(AgentType(agent_type))
        return {"templates": templates}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")


@router.get("/templates/tag/{tag}")
def get_templates_by_tag(tag: str):
    """按标签获取模板"""
    templates = agent_service.get_templates_by_tag(tag)
    return {"templates": templates}


@router.post("/templates")
def create_template(data: CreateTemplateRequest):
    """创建自定义模板"""
    template = agent_service.create_custom_template(data.model_dump())
    return template


@router.post("/")
def create_agent(data: CreateAgentRequest):
    """从模板创建 Agent"""
    try:
        agent = agent_service.create_agent(data.template_id, data.name)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/from-soul")
def create_agent_from_soul(data: CreateAgentFromSoulRequest):
    """从 soul.md 文件直接创建 Agent"""
    try:
        agent = agent_service.create_agent_from_soul(data.soul_name, data.name)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/soul-based")
def get_soul_based_agents():
    """获取所有基于 soul.md 的 Agent"""
    return {
        "agents": agent_service.get_soul_based_agents(),
        "total": len(agent_service.get_soul_based_agents())
    }


@router.get("/")
def list_agents():
    """列出所有 Agent"""
    return {
        "agents": agent_service.list_agents(),
        "total": len(agent_service.list_agents())
    }


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    """获取指定 Agent"""
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}")
def update_agent(agent_id: str, updates: dict):
    """更新 Agent"""
    agent = agent_service.update_agent(agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}")
def delete_agent(agent_id: str):
    """删除 Agent"""
    if not agent_service.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True}


@router.post("/teams")
def create_team(data: CreateTeamRequest):
    """创建团队"""
    team = agent_service.create_team(data.name, data.agent_ids)
    return team


@router.get("/teams")
def list_teams():
    """列出所有团队"""
    return {
        "teams": agent_service.list_teams()
    }


@router.get("/teams/{team_id}")
def get_team(team_id: str):
    """获取指定团队"""
    team = agent_service.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team
