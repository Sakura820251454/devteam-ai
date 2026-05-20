"""
Agent 管理 API 路由
提供 Agent 模板和实例的管理接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.agent.agent_service import agent_service, AgentType

router = APIRouter(prefix="/api/agents", tags=["Agent管理"])


class LLMConfigRequest(BaseModel):
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: Optional[int] = None


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
    llm_config: Optional[LLMConfigRequest] = None


class CreateAgentRequest(BaseModel):
    template_id: str
    name: Optional[str] = None
    llm_config: Optional[LLMConfigRequest] = None


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    status: Optional[str] = None
    llm_config: Optional[LLMConfigRequest] = None


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
        llm_config = data.llm_config.model_dump() if data.llm_config else None
        agent = agent_service.create_agent(data.template_id, data.name, llm_config)
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
def list_agents(available: bool = False, project_id: str = None):
    """列出 Agent，支持按可用状态和项目筛选"""
    if available:
        agents = agent_service.list_available_agents()
    elif project_id:
        agents = agent_service.get_project_agents(project_id)
    else:
        agents = agent_service.list_agents()
    return {
        "agents": agents,
        "total": len(agents)
    }


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    """获取指定 Agent"""
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}")
def update_agent(agent_id: str, updates: UpdateAgentRequest):
    """更新 Agent"""
    update_data = updates.model_dump(exclude_none=True)
    if "llm_config" in update_data and update_data["llm_config"] is not None:
        update_data["llm_config"] = updates.llm_config.model_dump()
    agent = agent_service.update_agent(agent_id, update_data)
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


# ========== Agent-Project 绑定 ==========

class AssignAgentRequest(BaseModel):
    project_id: str


@router.post("/{agent_id}/assign")
def assign_agent_to_project(agent_id: str, data: AssignAgentRequest):
    """将 Agent 分配到项目"""
    success = agent_service.assign_agent_to_project(agent_id, data.project_id)
    if not success:
        agent = agent_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        current = agent.get("assigned_project")
        raise HTTPException(
            status_code=409,
            detail=f"Agent 已在项目 {current} 中，无法分配到项目 {data.project_id}"
        )
    return {"status": "assigned", "agent_id": agent_id, "project_id": data.project_id}


@router.post("/{agent_id}/release")
def release_agent_from_project(agent_id: str, data: AssignAgentRequest):
    """从项目释放 Agent"""
    success = agent_service.release_agent_from_project(agent_id, data.project_id)
    if not success:
        raise HTTPException(status_code=400, detail="Agent 不在该项目中")
    return {"status": "released", "agent_id": agent_id, "project_id": data.project_id}


@router.get("/{agent_id}/project")
def get_agent_project(agent_id: str):
    """获取 Agent 当前所在项目"""
    project_id = agent_service.get_agent_project(agent_id)
    if not project_id:
        return {"agent_id": agent_id, "project_id": None, "status": "available"}
    return {"agent_id": agent_id, "project_id": project_id, "status": "busy"}
