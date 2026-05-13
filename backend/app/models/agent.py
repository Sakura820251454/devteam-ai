from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class LLMProviderType(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    MOCK = "mock"


class LLMConfig(BaseModel):
    provider: LLMProviderType = Field(default=LLMProviderType.MOCK, description="LLM提供商")
    model: str = Field(default="mock-model", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")

    class Config:
        use_enum_values = True


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    STOPPED = "stopped"


class PersonalityType(str, Enum):
    RIGOROUS = "严谨型"
    CREATIVE = "创意型"
    PRAGMATIC = "务实型"
    COLLABORATIVE = "协作型"


class CommunicationStyle(str, Enum):
    CONCISE = "简洁直接"
    DETAILED = "详细解释"
    HUMOROUS = "幽默风趣"


class SkillLevel(str, Enum):
    MASTERED = "精通"
    PROFICIENT = "熟练"
    FAMILIAR = "了解"


class AgentConfig(BaseModel):
    name: str = Field(..., description="Agent名称")
    role: str = Field(..., description="Agent角色")
    title: str = Field(default="中级", description="职称")
    backstory: str = Field(default="", description="背景故事")
    
    personality_type: PersonalityType = Field(default=PersonalityType.RIGOROUS, description="性格类型")
    communication_style: CommunicationStyle = Field(default=CommunicationStyle.DETAILED, description="沟通风格")
    confidence: int = Field(default=80, ge=0, le=100, description="自信度")
    proactivity: int = Field(default=70, ge=0, le=100, description="积极性")
    
    skills: Dict[str, SkillLevel] = Field(default_factory=dict, description="技能列表")
    knowledge_areas: List[str] = Field(default_factory=list, description="知识领域")
    task_preferences: List[str] = Field(default_factory=list, description="任务偏好")
    
    max_messages_per_round: int = Field(default=3, ge=1, description="每轮最多发言次数")
    min_interval: int = Field(default=5, ge=1, description="最短发言间隔(秒)")
    can_multi_task: bool = Field(default=False, description="是否可兼任")
    
    llm_config: Optional[LLMConfig] = Field(default=None, description="Agent的LLM配置，为None时使用全局默认配置")


class Agent(BaseModel):
    id: str
    config: AgentConfig
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    current_task: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def build_system_prompt(self) -> str:
        prompt_parts = [
            f"你是一个名为{self.config.name}的{self.config.role}，职称是{self.config.title}。",
            f"性格特点：{self.config.personality_type.value}，沟通风格：{self.config.communication_style.value}。",
        ]
        
        if self.config.backstory:
            prompt_parts.append(f"背景：{self.config.backstory}")
        
        if self.config.skills:
            skills_text = "、".join([f"{skill}({level.value})" for skill, level in self.config.skills.items()])
            prompt_parts.append(f"专业技能：{skills_text}")
        
        if self.config.knowledge_areas:
            areas_text = "、".join(self.config.knowledge_areas)
            prompt_parts.append(f"知识领域：{areas_text}")
        
        prompt_parts.append("你是开发团队的一员，与其他Agent协作完成开发任务。")
        prompt_parts.append("请保持你的性格特点和专业角色，用你的沟通风格进行交流。")
        
        return "\n".join(prompt_parts)


def create_default_developer_agent() -> Agent:
    return Agent(
        id="dev-default-001",
        config=AgentConfig(
            name="开发者小王",
            role="后端开发",
            title="中级工程师",
            backstory="3年后端开发经验，熟悉Python和FastAPI，擅长编写清晰易维护的代码。",
            personality_type=PersonalityType.RIGOROUS,
            communication_style=CommunicationStyle.DETAILED,
            skills={
                "Python": SkillLevel.MASTERED,
                "FastAPI": SkillLevel.MASTERED,
                "SQL": SkillLevel.PROFICIENT,
                "Docker": SkillLevel.PROFICIENT,
            },
            knowledge_areas=["后端架构", "API设计", "数据库优化"],
            task_preferences=["编码实现", "代码审查", "技术文档"],
        )
    )
