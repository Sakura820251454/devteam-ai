"""
Agent 配置管理服务
功能：
1. Agent 模板管理（预设 + 自定义）- 优先从 soul.md 加载
2. Agent 实例管理
3. 团队配置管理

Agent 模板是经过验证的最佳实践配置，包含：
- 角色定义
- 系统提示词
- 能力描述
- 协作风格

**数据源优先级**:
1. soul.md 文件（优先）- 从 agents/ 目录加载
2. 预设模板（fallback）- 代码中定义的默认模板
"""

from typing import Dict, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import uuid
import os
from pathlib import Path

from app.services.shared.soul_parser import load_all_agents as load_soul_agents, SoulFile
from app.models.session import Session, SessionStatus, Message as SessionMessage, MessageType
from app.core.llm import Message as LLMMessage
from app.services.shared.prompt_registry import registry


class AgentType(Enum):
    """Agent 类型"""
    PM = "product_manager"           # 产品经理
    ARCHITECT = "architect"          # 架构师
    BACKEND = "backend_developer"    # 后端开发
    FRONTEND = "frontend_developer"  # 前端开发
    TESTER = "tester"                # 测试工程师
    DEVOPS = "devops"                # 运维工程师
    CUSTOM = "custom"                # 自定义


@dataclass
class AgentTemplate:
    """Agent 模板定义"""
    id: str
    name: str                          # Agent 名称
    type: AgentType                    # Agent 类型
    description: str                   # 简短描述
    avatar_color: str                 # 头像颜色

    # 系统提示词 - 定义 Agent 的角色和行为
    system_prompt: str

    # 能力描述
    capabilities: List[str]           # 核心能力列表

    # 协作风格
    collaboration_style: str           # 如：主动型、被动型、分析型

    # 发言倾向
    speaking_tendency: str             # 如：简洁型、详细型

    # 预设标签（用于分类筛选）
    tags: List[str] = field(default_factory=list)

    # 是否为系统预设模板
    is_preset: bool = True

    # 适用场景
    suitable_scenarios: List[str] = field(default_factory=list)

    # 从 soul.md 加载的原始数据（保留引用）
    soul_data: Optional[SoulFile] = None


class AgentService:
    """Agent 服务"""

    def __init__(self):
        self._templates: Dict[str, AgentTemplate] = {}
        self._agents: Dict[str, Dict] = {}
        self._teams: Dict[str, List[str]] = {}  # team_id -> [agent_ids]
        self._sessions: Dict[str, Session] = {}
        self._project_agents: Dict[str, set] = {}  # project_id -> set of agent_ids
        self._session_db = None

        # 优先从 soul.md 加载，然后加载预设模板作为 fallback
        self._load_from_soul_files()
        self._load_preset_templates()

    def initialize(self, session_db=None) -> None:
        if session_db:
            self._session_db = session_db

    async def load_all_sessions(self) -> None:
        if self._session_db:
            self._sessions = await self._session_db.load_all_sessions()

    def _load_from_soul_files(self):
        """从 soul.md 文件加载 Agent 定义（优先数据源）"""
        try:
            # 获取 agents 目录路径
            agents_dir = Path(__file__).parent.parent.parent.parent / "agents"

            if agents_dir.exists():
                # 从 soul_parser 加载所有 Agent
                soul_agents = load_soul_agents(str(agents_dir))

                for name, soul in soul_agents.items():
                    # 将 soul.md 转换为 AgentTemplate
                    template = self._soul_to_template(soul)
                    if template:
                        # 使用 soul.md 中的名称作为模板 ID（优先）
                        self._templates[template.id] = template

                        # 同时自动创建 Agent 实例，使其出现在人才库中
                        agent_id = f"soul_{soul.name}"
                        self._agents[agent_id] = {
                            "id": agent_id,
                            "template_id": template.id,
                            "name": soul.name,
                            "type": "custom",
                            "description": template.description,
                            "avatar_color": template.avatar_color,
                            "system_prompt": template.system_prompt,
                            "capabilities": template.capabilities,
                            "status": "idle",
                            "is_active": True,
                            "source": "soul",
                            "assigned_project": None,
                            "project_history": [],
                            "soul_data": {
                                "name": soul.name,
                                "core_principles": soul.core_principles,
                                "execution_rules": soul.execution_rules,
                                "role_definitions": soul.role_definitions
                            }
                        }
        except Exception as e:
            print(f"Error loading agents from soul files: {e}")

    def _soul_to_template(self, soul: SoulFile) -> Optional[AgentTemplate]:
        """将 SoulFile 转换为 AgentTemplate"""
        agent_type = AgentType.CUSTOM
        
        # 构建系统提示词
        system_prompt = self._build_prompt_from_soul(soul)
        
        # 从角色定义中提取能力
        capabilities = []
        if soul.role_definitions:
            if 'skills' in soul.role_definitions:
                capabilities.extend(soul.role_definitions['skills'])
        
        return AgentTemplate(
            id=f"soul_{soul.name}",
            name=soul.name,
            type=agent_type,
            description=soul.title if soul.title else f"{soul.name} - 基于 soul.md 定义",
            avatar_color=soul.avatar_color if soul.avatar_color else "#6B7280",
            system_prompt=system_prompt,
            capabilities=capabilities if capabilities else ["根据 soul.md 定义的能力"],
            collaboration_style="分析型",
            speaking_tendency="详细型",
            tags=["soul-based", soul.name],
            is_preset=False,
            suitable_scenarios=["基于 soul.md 定义的场景"],
            soul_data=soul
        )

    def _infer_agent_type(self, name: str) -> AgentType:
        """Agent 类型统一为 CUSTOM——配置阶段不预设职位。"""
        return AgentType.CUSTOM

    def _build_prompt_from_soul(self, soul: SoulFile) -> str:
        """从 SoulFile 构建系统提示词"""
        from app.services.shared.soul_parser import soul_to_system_prompt
        return soul_to_system_prompt(soul)

    def _load_preset_templates(self):
        """加载预设模板（fallback）"""
        presets = get_preset_templates()
        for template in presets:
            # 仅当 soul.md 中没有同名模板时才添加预设模板
            if template.id not in self._templates:
                self._templates[template.id] = template

    # ========== 模板管理 ==========

    def get_all_templates(self, include_preset: bool = True, include_custom: bool = True) -> List[Dict]:
        """获取所有模板"""
        result = []
        for template in self._templates.values():
            if template.is_preset and include_preset:
                result.append(self._template_to_dict(template))
            elif not template.is_preset and include_custom:
                result.append(self._template_to_dict(template))
        return result

    def get_template(self, template_id: str) -> Optional[Dict]:
        """获取指定模板"""
        template = self._templates.get(template_id)
        if template:
            return self._template_to_dict(template)
        return None

    def get_templates_by_type(self, agent_type: AgentType) -> List[Dict]:
        """按类型获取模板"""
        return [
            self._template_to_dict(t)
            for t in self._templates.values()
            if t.type == agent_type
        ]

    def get_templates_by_tag(self, tag: str) -> List[Dict]:
        """按标签获取模板"""
        return [
            self._template_to_dict(t)
            for t in self._templates.values()
            if tag in t.tags
        ]

    def create_custom_template(self, template_data: Dict) -> Dict:
        """创建自定义模板"""
        template = AgentTemplate(
            id=f"custom_{uuid.uuid4().hex[:8]}",
            name=template_data["name"],
            type=AgentType(template_data.get("type", "custom")),
            description=template_data.get("description", ""),
            avatar_color=template_data.get("avatar_color", "#6B7280"),
            system_prompt=template_data["system_prompt"],
            capabilities=template_data.get("capabilities", []),
            collaboration_style=template_data.get("collaboration_style", ""),
            speaking_tendency=template_data.get("speaking_tendency", ""),
            tags=template_data.get("tags", []),
            is_preset=False,
            suitable_scenarios=template_data.get("suitable_scenarios", [])
        )
        self._templates[template.id] = template
        return self._template_to_dict(template)

    def _template_to_dict(self, template: AgentTemplate) -> Dict:
        """模板转字典"""
        return {
            "id": template.id,
            "name": template.name,
            "type": template.type.value,
            "description": template.description,
            "avatar_color": template.avatar_color,
            "system_prompt": template.system_prompt,
            "capabilities": template.capabilities,
            "collaboration_style": template.collaboration_style,
            "speaking_tendency": template.speaking_tendency,
            "tags": template.tags,
            "is_preset": template.is_preset,
            "suitable_scenarios": template.suitable_scenarios
        }

    # ========== Agent 实例管理 ==========

    def create_agent(self, template_id: str, name: Optional[str] = None, llm_config: Optional[dict] = None) -> Dict:
        """从模板创建 Agent 实例"""
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        agent = {
            "id": agent_id,
            "template_id": template_id,
            "name": name or template.name,
            "type": template.type.value,
            "description": template.description,
            "avatar_color": template.avatar_color,
            "system_prompt": template.system_prompt,
            "capabilities": template.capabilities,
            "status": "idle",
            "is_active": True,
            "source": "template",
            "soul_data": None,
            "llm_config": llm_config,
            "assigned_project": None,
            "project_history": [],
        }
        
        # 如果模板是从 soul.md 加载的，保留 soul 数据
        if template.soul_data:
            agent["source"] = "soul"
            agent["soul_data"] = {
                "name": template.soul_data.name,
                "core_principles": template.soul_data.core_principles,
                "execution_rules": template.soul_data.execution_rules,
                "role_definitions": template.soul_data.role_definitions
            }
        
        self._agents[agent_id] = agent
        return agent

    def create_agent_from_soul(self, soul_name: str, name: Optional[str] = None) -> Dict:
        """直接从 soul.md 文件创建 Agent 实例"""
        from app.services.shared.soul_parser import load_agent_from_soul
        from pathlib import Path
        
        # 查找 soul 文件
        agents_dir = Path(__file__).parent.parent.parent.parent / "agents"
        soul_file_path = agents_dir / f"agent_{soul_name}" / "soul.md"
        
        if not soul_file_path.exists():
            raise ValueError(f"Soul file not found for agent: {soul_name}")
        
        # 加载 soul 数据
        soul = load_agent_from_soul(str(soul_file_path))
        
        # 转换为模板
        template = self._soul_to_template(soul)
        
        # 创建 Agent
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        agent = {
            "id": agent_id,
            "template_id": f"soul_{soul.name}",
            "name": name or soul.name,
            "type": template.type.value,
            "description": template.description,
            "avatar_color": template.avatar_color,
            "system_prompt": template.system_prompt,
            "capabilities": template.capabilities,
            "status": "idle",
            "is_active": True,
            "source": "soul",
            "assigned_project": None,
            "project_history": [],
            "soul_data": {
                "name": soul.name,
                "core_principles": soul.core_principles,
                "execution_rules": soul.execution_rules,
                "role_definitions": soul.role_definitions
            }
        }
        
        self._agents[agent_id] = agent
        return agent

    def get_soul_based_agents(self) -> List[Dict]:
        """获取所有基于 soul.md 的 Agent"""
        return [
            agent for agent in self._agents.values()
            if agent.get("source") == "soul"
        ]

    def create_agent_context(self, agent_id: str, session_id: str):
        """为 Agent 创建上下文（集成 soul 数据）"""
        from app.models.agent_context import AgentContextFactory, AgentContext
        
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        
        # 如果 Agent 有 soul 数据，使用 soul 创建上下文
        if agent.get("soul_data"):
            from app.services.shared.soul_parser import SoulFile
            soul = SoulFile(
                name=agent["soul_data"]["name"],
                core_principles=agent["soul_data"]["core_principles"],
                execution_rules=agent["soul_data"]["execution_rules"],
                role_definitions=agent["soul_data"].get("role_definitions", {})
            )
            context = AgentContextFactory.from_soul_file(soul, session_id)
            # 确保使用正确的 agent_id
            context.agent_id = agent_id
            return context
        else:
            # 否则使用普通方式创建
            return AgentContextFactory.create(
                agent_id=agent_id,
                session_id=session_id,
                role=agent.get("name", "agent"),
                system_prompt=agent.get("system_prompt", "")
            )

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """获取 Agent"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict]:
        """列出所有 Agent"""
        return list(self._agents.values())

    def update_agent(self, agent_id: str, updates: Dict) -> Optional[Dict]:
        """更新 Agent"""
        if agent_id not in self._agents:
            return None
        self._agents[agent_id].update(updates)
        return self._agents[agent_id]

    def delete_agent(self, agent_id: str) -> bool:
        """删除 Agent"""
        if agent_id in self._agents:
            # Release from any project first
            project = self._agents[agent_id].get("assigned_project")
            if project:
                self.release_agent_from_project(agent_id, project)
            del self._agents[agent_id]
            return True
        return False

    # ========== Agent-Project 绑定 ==========

    def assign_agent_to_project(self, agent_id: str, project_id: str) -> bool:
        """将 Agent 分配到项目（同一时间只能在一个项目）"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent_name = agent.get("name", agent_id)
        current = agent.get("assigned_project")
        if current == project_id:
            return True
        if current is not None:
            return False  # 已在其他项目中
        agent["assigned_project"] = project_id
        agent["project_history"].append({
            "project_id": project_id,
            "assigned_at": __import__("datetime").datetime.now().isoformat(),
            "released_at": None
        })
        self._project_agents.setdefault(project_id, set()).add(agent_id)

        # 记录分配日志
        try:
            from app.services.project.workspace_manager import workspace_manager
            workspace_manager.add_log(project_id, "info", "agent_service",
                f"Agent [{agent_name}] 已分配到项目 (角色: {agent.get('type', '未指定')})")
        except Exception:
            pass

        return True

    def release_agent_from_project(self, agent_id: str, project_id: str) -> bool:
        """从项目释放 Agent"""
        agent = self._agents.get(agent_id)
        if not agent or agent.get("assigned_project") != project_id:
            return False
        agent_name = agent.get("name", agent_id)
        agent["assigned_project"] = None
        # Update history
        for entry in agent.get("project_history", []):
            if entry["project_id"] == project_id and entry["released_at"] is None:
                entry["released_at"] = __import__("datetime").datetime.now().isoformat()
        self._project_agents.get(project_id, set()).discard(agent_id)
        if project_id in self._project_agents and not self._project_agents[project_id]:
            del self._project_agents[project_id]

        # 记录释放日志
        try:
            from app.services.project.workspace_manager import workspace_manager
            workspace_manager.add_log(project_id, "info", "agent_service",
                f"Agent [{agent_name}] 已从项目释放")
        except Exception:
            pass

        return True

    def get_project_agents(self, project_id: str) -> List[Dict]:
        """获取项目中的所有 Agent"""
        agent_ids = self._project_agents.get(project_id, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_agent_project(self, agent_id: str) -> Optional[str]:
        """获取 Agent 当前所在项目"""
        agent = self._agents.get(agent_id)
        return agent.get("assigned_project") if agent else None

    def is_agent_available(self, agent_id: str) -> bool:
        """检查 Agent 是否空闲"""
        agent = self._agents.get(agent_id)
        return agent is not None and agent.get("assigned_project") is None

    def list_available_agents(self) -> List[Dict]:
        """列出所有空闲 Agent"""
        return [a for a in self._agents.values() if a.get("assigned_project") is None]

    def release_project_agents(self, project_id: str) -> int:
        """释放项目中所有 Agent，返回释放数量"""
        count = 0
        for agent_id in list(self._project_agents.get(project_id, set())):
            if self.release_agent_from_project(agent_id, project_id):
                count += 1
        return count

    # ========== 团队管理 ==========

    def create_team(self, name: str, agent_ids: List[str]) -> Dict:
        """创建团队"""
        team_id = f"team_{uuid.uuid4().hex[:8]}"
        self._teams[team_id] = {
            "id": team_id,
            "name": name,
            "agent_ids": agent_ids,
            "agents": [self._agents.get(aid) for aid in agent_ids if aid in self._agents]
        }
        return self._teams[team_id]

    def get_team(self, team_id: str) -> Optional[Dict]:
        """获取团队"""
        return self._teams.get(team_id)

    def list_teams(self) -> List[Dict]:
        """列出所有团队"""
        return [
            {
                "id": tid,
                "name": t["name"],
                "agent_count": len(t["agent_ids"])
            }
            for tid, t in self._teams.items()
        ]

    # ========== Session 管理 ==========

    async def create_session(
        self,
        title: str = "新会话",
        participant_ids: Optional[List[str]] = None
    ) -> Session:
        """创建会话"""
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        session = Session(
            id=session_id,
            title=title,
            participants=participant_ids or []
        )
        self._sessions[session_id] = session
        if self._session_db:
            await self._session_db.save_session(session)
        return session

    def list_sessions(self) -> List[Session]:
        """列出所有会话"""
        return list(self._sessions.values())

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取指定会话"""
        return self._sessions.get(session_id)

    # ========== Chat 方法 ==========

    async def agent_chat(
        self,
        agent_id: str,
        session_id: str,
        user_message: str
    ) -> str:
        """Agent 聊天（非流式）"""
        from app.services.llm.llm_service import llm_service

        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Add user message to session
        user_msg = SessionMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            sender_id="user",
            sender_name="User",
            content=user_message,
            message_type=MessageType.TEXT
        )
        session.add_message(user_msg)
        if self._session_db:
            await self._session_db.save_message(user_msg)

        # Build LLM messages with system prompt
        system_prompt = agent.get("system_prompt") or registry.render("agent.service.chat_fallback", {})
        llm_messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message)
        ]

        # Build Agent model with llm_config so LLMService can use per-agent settings
        agent_model = None
        agent_llm_config = agent.get("llm_config")
        if agent_llm_config:
            from app.models.agent import Agent as AgentModel, AgentConfig as AgentConfigModel, LLMConfig as AgentLLMConfig
            agent_model = AgentModel(
                id=agent["id"],
                config=AgentConfigModel(
                    name=agent.get("name", "Agent"),
                    role=agent.get("name", "agent"),
                    llm_config=AgentLLMConfig(
                        provider=agent_llm_config.get("provider", "deepseek"),
                        model=agent_llm_config.get("model", "deepseek-v4-flash"),
                        temperature=agent_llm_config.get("temperature", 0.7),
                        max_tokens=agent_llm_config.get("max_tokens"),
                    )
                )
            )

        response = await llm_service.chat(llm_messages, agent=agent_model)

        # Add assistant response to session
        assistant_msg = SessionMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            sender_id=agent_id,
            sender_name=agent.get("name", "Agent"),
            content=response.content,
            message_type=MessageType.TEXT
        )
        session.add_message(assistant_msg)
        if self._session_db:
            await self._session_db.save_message(assistant_msg)

        return response.content

    async def agent_chat_stream(
        self,
        agent_id: str,
        session_id: str,
        user_message: str
    ) -> AsyncIterator[str]:
        """Agent 聊天（流式）"""
        from app.services.llm.llm_service import llm_service

        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Add user message to session
        user_msg = SessionMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            sender_id="user",
            sender_name="User",
            content=user_message,
            message_type=MessageType.TEXT
        )
        session.add_message(user_msg)
        if self._session_db:
            await self._session_db.save_message(user_msg)

        # Build LLM messages
        system_prompt = agent.get("system_prompt") or registry.render("agent.service.chat_fallback", {})
        llm_messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message)
        ]

        # Build Agent model with llm_config so LLMService can use per-agent settings
        agent_model = None
        agent_llm_config = agent.get("llm_config")
        if agent_llm_config:
            from app.models.agent import Agent as AgentModel, AgentConfig as AgentConfigModel, LLMConfig as AgentLLMConfig
            agent_model = AgentModel(
                id=agent["id"],
                config=AgentConfigModel(
                    name=agent.get("name", "Agent"),
                    role=agent.get("name", "agent"),
                    llm_config=AgentLLMConfig(
                        provider=agent_llm_config.get("provider", "deepseek"),
                        model=agent_llm_config.get("model", "deepseek-v4-flash"),
                        temperature=agent_llm_config.get("temperature", 0.7),
                        max_tokens=agent_llm_config.get("max_tokens"),
                    )
                )
            )

        full_response = ""
        async for chunk in llm_service.stream_chat(llm_messages, agent=agent_model):
            full_response += chunk
            yield chunk

        # Add assistant response to session
        assistant_msg = SessionMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            sender_id=agent_id,
            sender_name=agent.get("name", "Agent"),
            content=full_response,
            message_type=MessageType.TEXT
        )
        session.add_message(assistant_msg)
        if self._session_db:
            await self._session_db.save_message(assistant_msg)


def get_preset_templates() -> List[AgentTemplate]:
    """
    获取预设 Agent 通用模板。
    不预设具体角色——角色由 soul.md 定义，trait_service 动态分析。
    此模板仅作为 soul.md 不可用时的最小兜底。
    """
    return [
        AgentTemplate(
            id="generic_default",
            name="开发团队成员",
            type=AgentType.BACKEND,  # 通用类型，实际角色由 trait_service 动态确定
            description="通用开发团队成员，不预设具体角色",
            avatar_color="#6B7280",  # 灰色 — 未分配具体角色
            system_prompt="你是 DevTeam AI 开发团队的一员。\n\n保持简洁，直接解决问题。\n遇到问题先动手排查，排查不出来再用工具查找，实在找不到才问用户。",
            capabilities=[],  # 由 trait_service 从 soul.md 动态分析
            collaboration_style="务实型",
            speaking_tendency="简洁型",
            tags=["通用"],
            is_preset=True,
            suitable_scenarios=["通用任务执行"]
        ),
    ]


# 全局实例
agent_service = AgentService()
