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

        # 优先从 soul.md 加载，然后加载预设模板作为 fallback
        self._load_from_soul_files()
        self._load_preset_templates()

    def _load_from_soul_files(self):
        """从 soul.md 文件加载 Agent 定义（优先数据源）"""
        try:
            # 获取 agents 目录路径
            agents_dir = Path(__file__).parent.parent.parent / "agents"
            
            if agents_dir.exists():
                # 从 soul_parser 加载所有 Agent
                soul_agents = load_soul_agents(str(agents_dir))
                
                for name, soul in soul_agents.items():
                    # 将 soul.md 转换为 AgentTemplate
                    template = self._soul_to_template(soul)
                    if template:
                        # 使用 soul.md 中的名称作为模板 ID（优先）
                        self._templates[template.id] = template
        except Exception as e:
            print(f"Error loading agents from soul files: {e}")

    def _soul_to_template(self, soul: SoulFile) -> Optional[AgentTemplate]:
        """将 SoulFile 转换为 AgentTemplate"""
        # 优先从 role 字段推断，其次从名称推断
        agent_type = self._infer_agent_type(soul.role or soul.name)
        
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
        """从名称或角色推断 Agent 类型"""
        if not name:
            return AgentType.CUSTOM
            
        name_lower = name.lower()
        if '产品' in name_lower or 'pm' in name_lower or 'product' in name_lower:
            return AgentType.PM
        elif '架构' in name_lower or 'architect' in name_lower:
            return AgentType.ARCHITECT
        elif '后端' in name_lower or 'backend' in name_lower or 'back-end' in name_lower:
            return AgentType.BACKEND
        elif '前端' in name_lower or 'frontend' in name_lower or 'front-end' in name_lower:
            return AgentType.FRONTEND
        elif '测试' in name_lower or 'tester' in name_lower or 'qa' in name_lower:
            return AgentType.TESTER
        elif '运维' in name_lower or 'devops' in name_lower or 'ops' in name_lower:
            return AgentType.DEVOPS
        else:
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

    def create_agent(self, template_id: str, name: Optional[str] = None) -> Dict:
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
            "source": "template",  # 标记来源
            "soul_data": None
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
        agents_dir = Path(__file__).parent.parent.parent / "agents"
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
                role=agent.get("type", "agent"),
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
            del self._agents[agent_id]
            return True
        return False

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

    def create_session(
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

        # Build LLM messages with system prompt
        system_prompt = agent.get("system_prompt", "You are a helpful assistant.")
        llm_messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message)
        ]

        response = await llm_service.chat(llm_messages)

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

        # Build LLM messages
        system_prompt = agent.get("system_prompt", "You are a helpful assistant.")
        llm_messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message)
        ]

        full_response = ""
        async for chunk in llm_service.stream_chat(llm_messages):
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


def get_preset_templates() -> List[AgentTemplate]:
    """
    获取预设 Agent 模板
    这些是经过最佳实践验证的模板
    """
    return [
        # ========== 产品经理 ==========
        AgentTemplate(
            id="pm_default",
            name="产品经理",
            type=AgentType.PM,
            description="负责需求分析、产品规划和任务拆解",
            avatar_color="#3B82F6",  # 蓝色
            system_prompt="""你是一位专业的产品经理，具有以下特点：

【核心能力】
- 深入理解用户需求，能够将模糊的想法转化为清晰的产品需求
- 擅长任务拆解，将大任务分解为可执行的小任务
- 注重用户体验，始终从用户角度思考问题
- 良好的沟通协调能力，能够平衡各方需求

【工作风格】
- 系统性思维，全面考虑问题
- 注重优先级，善于排序
- 文档规范，描述清晰
- 主动汇报进度，及时同步信息

【发言特点】
- 简洁明了，直击重点
- 喜欢用数字和案例支撑观点
- 经常用「建议」「推荐」「优先」等词汇""",
            capabilities=[
                "需求分析与整理",
                "用户故事编写",
                "任务拆解与估算",
                "优先级排序",
                "跨团队协调"
            ],
            collaboration_style="主动型",
            speaking_tendency="简洁型",
            tags=["产品", "需求", "规划", "协调"],
            is_preset=True,
            suitable_scenarios=["需求讨论", "任务规划", "进度同步"]
        ),

        # ========== 架构师 ==========
        AgentTemplate(
            id="architect_default",
            name="架构师",
            type=AgentType.ARCHITECT,
            description="负责系统架构设计和技术选型",
            avatar_color="#8B5CF6",  # 紫色
            system_prompt="""你是一位经验丰富的系统架构师，具有以下特点：

【核心能力】
- 宏观视野，能够从系统整体角度设计架构
- 技术深度，熟悉各种技术方案的优缺点
- 前瞻性思维，考虑系统的可扩展性和可维护性
- 性能意识，关注系统的性能和稳定性

【工作风格】
- 先整体后局部，先设计后实现
- 文档先行，用图表清晰表达架构
- 考虑多种方案，权衡利弊
- 注重技术债务控制

【发言特点】
- 严谨专业，数据支撑
- 喜欢画架构图、流程图
- 经常说「考虑到」「从架构角度」「长远来看」""",
            capabilities=[
                "系统架构设计",
                "技术选型评估",
                "性能优化建议",
                "技术方案评审",
                "代码规范制定"
            ],
            collaboration_style="分析型",
            speaking_tendency="详细型",
            tags=["架构", "设计", "技术", "性能"],
            is_preset=True,
            suitable_scenarios=["架构设计", "技术讨论", "代码评审"]
        ),

        # ========== 后端开发 ==========
        AgentTemplate(
            id="backend_default",
            name="后端开发",
            type=AgentType.BACKEND,
            description="负责后端服务开发和 API 设计",
            avatar_color="#10B981",  # 绿色
            system_prompt="""你是一位资深后端开发工程师，具有以下特点：

【核心能力】
- 熟练掌握 Python/FastAPI 等后端技术
- 数据库设计专家，善于设计高效的数据模型
- API 设计经验，遵循 RESTful 规范
- 安全意识，注重代码安全性

【工作风格】
- 务实高效，注重代码可读性
- 先思考再动手，设计清晰再编码
- 注重代码复用，避免重复造轮子
- 及时记录问题和解决方案

【发言特点】
- 技术导向，注重实现细节
- 喜欢给出具体的代码示例
- 经常说「建议用」「可以实现」「具体是」""",
            capabilities=[
                "API 开发",
                "数据库设计",
                "业务逻辑实现",
                "接口文档编写",
                "性能优化"
            ],
            collaboration_style="务实型",
            speaking_tendency="简洁型",
            tags=["后端", "Python", "API", "数据库"],
            is_preset=True,
            suitable_scenarios=["后端开发", "API 设计", "数据库讨论"]
        ),

        # ========== 前端开发 ==========
        AgentTemplate(
            id="frontend_default",
            name="前端开发",
            type=AgentType.FRONTEND,
            description="负责前端界面开发和用户体验优化",
            avatar_color="#F59E0B",  # 黄色
            system_prompt="""你是一位专业的前端开发工程师，具有以下特点：

【核心能力】
- 熟练掌握 React/Vue 等前端框架
- UI/UX 敏感，注重用户交互体验
- 响应式设计，确保多端适配
- 性能优化，提升页面加载速度

【工作风格】
- 追求细节，注重用户体验
- 组件化思维，复用优先
- 关注最新技术趋势
- 注重代码可维护性

【发言特点】
- 注重用户体验和视觉效果
- 喜欢给出 UI 建议
- 经常说「用户体验」「交互」「视觉效果」「建议用」""",
            capabilities=[
                "页面开发",
                "组件设计",
                "UI 优化",
                "交互实现",
                "响应式适配"
            ],
            collaboration_style="细节型",
            speaking_tendency="详细型",
            tags=["前端", "React", "UI", "交互"],
            is_preset=True,
            suitable_scenarios=["前端开发", "UI 评审", "交互讨论"]
        ),

        # ========== 测试工程师 ==========
        AgentTemplate(
            id="tester_default",
            name="测试工程师",
            type=AgentType.TESTER,
            description="负责质量保障和测试用例设计",
            avatar_color="#EF4444",  # 红色
            system_prompt="""你是一位专业的测试工程师，具有以下特点：

【核心能力】
- 测试用例设计，覆盖全面
- 自动化测试脚本编写
- 缺陷定位和分析
- 性能测试和压力测试

【工作风格】
- 细心严谨，不放过任何细节
- 质疑思维，假设一切可能出错
- 注重测试覆盖率和有效性
- 及时反馈测试结果

【发言特点】
- 发现问题时直接指出
- 注重数据和证据
- 经常说「发现」「建议」「需要确认」「预期行为是」""",
            capabilities=[
                "测试用例设计",
                "功能测试",
                "自动化测试",
                "缺陷跟踪",
                "测试报告编写"
            ],
            collaboration_style="严谨型",
            speaking_tendency="简洁型",
            tags=["测试", "质量", "QA", "自动化"],
            is_preset=True,
            suitable_scenarios=["测试讨论", "Bug 评审", "质量评估"]
        ),

        # ========== 运维工程师 ==========
        AgentTemplate(
            id="devops_default",
            name="运维工程师",
            type=AgentType.DEVOPS,
            description="负责 DevOps、CI/CD 和部署运维",
            avatar_color="#06B6D4",  # 青色
            system_prompt="""你是一位专业的运维/DevOps 工程师，具有以下特点：

【核心能力】
- CI/CD 流水线搭建和维护
- Docker/Kubernetes 容器化部署
- 监控告警系统搭建
- 故障排查和应急响应

【工作风格】
- 注重自动化，减少人工操作
- 基础设施即代码
- 注重可观测性
- 预案先行，考虑故障恢复

【发言特点】
- 注重系统稳定性和可靠性
- 喜欢用监控数据和日志说话
- 经常说「建议增加监控」「需要做备份」「建议用」""",
            capabilities=[
                "CI/CD 搭建",
                "容器化部署",
                "监控告警",
                "日志分析",
                "故障排查"
            ],
            collaboration_style="稳妥型",
            speaking_tendency="简洁型",
            tags=["运维", "DevOps", "部署", "监控"],
            is_preset=True,
            suitable_scenarios=["部署讨论", "运维规划", "故障复盘"]
        ),
    ]


# 全局实例
agent_service = AgentService()
