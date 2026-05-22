from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class MemoryLevel(str, Enum):
    """记忆层级"""
    WORKING = "working"      # L1: 工作记忆 - 当前会话的短期记忆
    SHORT_TERM = "short_term" # L2: 短期记忆 - 最近几次会话的摘要
    LONG_TERM = "long_term"   # L3: 长期记忆 - 持久化的知识库


class MemoryEntry(BaseModel):
    """单个记忆条目"""
    id: str
    content: str
    level: MemoryLevel
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)
    relevance_score: float = Field(default=1.0)


class AgentContext(BaseModel):
    """Agent 的独立上下文"""
    agent_id: str
    session_id: str
    
    # 角色定义
    role: str
    system_prompt: str
    personality: Dict[str, Any] = Field(default_factory=dict)
    
    # 当前状态
    status: str = "idle"
    current_task: Optional[str] = None
    task_progress: float = 0.0
    
    # 对话历史（独立于会话）
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 记忆系统
    memory_entries: List[MemoryEntry] = Field(default_factory=list)
    
    # 上下文窗口（用于LLM调用）
    context_window: List[str] = Field(default_factory=list)
    max_context_tokens: int = 8192
    
    # 统计信息
    messages_sent: int = 0
    tokens_used: int = 0
    last_active_at: datetime = Field(default_factory=datetime.now)
    
    # 原始 soul 数据引用（保留用于后续使用）
    soul_data: Optional[Any] = None


class AgentMemoryManager:
    """Agent 记忆管理器"""
    
    def __init__(self, agent_context: AgentContext):
        self.context = agent_context
    
    def add_memory(self, content: str, level: MemoryLevel = MemoryLevel.WORKING, tags: List[str] = None):
        """添加记忆"""
        entry = MemoryEntry(
            id=f"mem_{datetime.now().timestamp()}",
            content=content,
            level=level,
            tags=tags or []
        )
        self.context.memory_entries.append(entry)
        
        # 如果是工作记忆，添加到上下文窗口
        if level == MemoryLevel.WORKING:
            self._update_context_window(content)
    
    def _update_context_window(self, content: str):
        """更新上下文窗口，保持在token限制内"""
        self.context.context_window.append(content)
        
        # 简单的token计算和截断
        total_tokens = sum(len(text) // 4 for text in self.context.context_window)
        while total_tokens > self.context.max_context_tokens and len(self.context.context_window) > 0:
            removed = self.context.context_window.pop(0)
            total_tokens -= len(removed) // 4
    
    def retrieve_relevant_memory(self, query: str, max_results: int = 5) -> List[MemoryEntry]:
        """检索相关记忆（简单实现：基于标签匹配）"""
        relevant = [
            entry for entry in self.context.memory_entries
            if any(tag.lower() in query.lower() for tag in entry.tags)
            or any(word.lower() in entry.content.lower() for word in query.split())
        ]
        
        # 按相关性分数排序
        relevant.sort(key=lambda x: x.relevance_score, reverse=True)
        return relevant[:max_results]
    
    def get_context_prompt(self) -> str:
        """生成包含记忆的上下文提示词"""
        parts = []
        
        # 添加工作记忆
        if self.context.context_window:
            parts.append("# Working Memory")
            parts.append("\n".join(self.context.context_window[-10:]))
        
        # 添加短期记忆摘要
        short_term_memories = [
            e for e in self.context.memory_entries
            if e.level == MemoryLevel.SHORT_TERM
        ]
        if short_term_memories:
            parts.append("\n# Recent Learnings")
            for mem in short_term_memories[-5:]:
                parts.append(f"- {mem.content}")
        
        return "\n".join(parts)
    
    def summarize_conversation(self):
        """生成会话摘要并保存到短期记忆"""
        if len(self.context.conversation_history) < 3:
            return
        
        # 生成摘要（简化实现）
        recent_messages = self.context.conversation_history[-10:]
        summary = self._generate_summary(recent_messages)
        
        if summary:
            self.add_memory(summary, MemoryLevel.SHORT_TERM, tags=["summary", "conversation"])
    
    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """简单的摘要生成"""
        if not messages:
            return ""
        
        topics = set()
        for msg in messages:
            content = msg.get("content", "")
            if len(content) > 10:
                topics.add(content[:50])
        
        if topics:
            return f"会话要点: {', '.join(list(topics)[:3])}"
        return ""


class SharedSessionContext(BaseModel):
    """会话级别的共享上下文"""
    session_id: str
    participants: List[str] = Field(default_factory=list)
    shared_knowledge: List[str] = Field(default_factory=list)
    team_goals: List[str] = Field(default_factory=list)
    conversation_rules: List[str] = Field(default_factory=list)
    
    def add_shared_knowledge(self, knowledge: str):
        """添加共享知识"""
        if knowledge not in self.shared_knowledge:
            self.shared_knowledge.append(knowledge)


class AgentContextFactory:
    """Agent 上下文工厂"""
    
    @staticmethod
    def create(agent_id: str, session_id: str, role: str, system_prompt: str) -> AgentContext:
        """创建新的 Agent 上下文"""
        return AgentContext(
            agent_id=agent_id,
            session_id=session_id,
            role=role,
            system_prompt=system_prompt
        )
    
    @staticmethod
    def from_soul(soul_data: dict, session_id: str) -> AgentContext:
        """从 soul.md 数据创建上下文（兼容字典格式）"""
        return AgentContext(
            agent_id=soul_data.get("name", "unknown"),
            session_id=session_id,
            role="agent",
            system_prompt=soul_data.get("system_prompt", ""),
            personality={
                "core_principles": soul_data.get("core_principles", []),
                "execution_rules": soul_data.get("execution_rules", [])
            },
            soul_data=soul_data
        )
    
    @staticmethod
    def from_soul_file(soul_file, session_id: str) -> AgentContext:
        """从 SoulFile 对象创建上下文（推荐方式）"""
        from app.services.shared.soul_parser import soul_to_system_prompt
        
        system_prompt = soul_to_system_prompt(soul_file)
        
        return AgentContext(
            agent_id=soul_file.name,
            session_id=session_id,
            role="agent",
            system_prompt=system_prompt,
            personality={
                "core_principles": soul_file.core_principles,
                "execution_rules": soul_file.execution_rules,
                "role_definitions": soul_file.role_definitions
            },
            soul_data=soul_file
        )
