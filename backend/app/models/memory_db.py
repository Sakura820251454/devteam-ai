from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class MemoryLevel(str):
    """记忆层级枚举"""
    WORKING = "working"      # L1: 工作记忆 - 当前会话
    SHORT_TERM = "short_term"  # L2: 短期记忆 - 最近会话摘要
    LONG_TERM = "long_term"    # L3: 长期记忆 - 持久化知识


class MemoryEntryModel(Base):
    """记忆条目模型 - 持久化存储"""
    __tablename__ = "memory_entries"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    content = Column(Text, nullable=False)
    level = Column(String, nullable=False, default=MemoryLevel.WORKING)
    
    tags = Column(JSON, default=list)
    relevance_score = Column(Float, default=1.0)
    usage_count = Column(Integer, default=0)
    source = Column(String, nullable=True)
    extra_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.now)
    last_accessed_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_memory_agent_level", "agent_id", "level"),
        Index("idx_memory_created", "created_at"),
    )

    def __repr__(self):
        return f"<MemoryEntry(id={self.id}, agent_id={self.agent_id}, level={self.level})>"


class AgentContextModel(Base):
    """Agent 上下文模型 - 持久化存储"""
    __tablename__ = "agent_contexts"

    agent_id = Column(String, primary_key=True, index=True)
    session_id = Column(String, nullable=True)
    
    role = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=True)
    personality = Column(JSON, default=dict)
    
    status = Column(String, default="idle")
    current_task = Column(String, nullable=True)
    task_progress = Column(Float, default=0.0)
    
    max_context_tokens = Column(Integer, default=8192)
    messages_sent = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    
    last_active_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<AgentContext(agent_id={self.agent_id}, status={self.status})>"


class TrajectoryModel(Base):
    """轨迹记录模型 - Phase 4.3"""
    __tablename__ = "trajectories"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    task_id = Column(String, nullable=True, index=True)
    
    content = Column(Text, nullable=False)
    decisions = Column(JSON, default=list)
    outcomes = Column(JSON, default=dict)
    success = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Trajectory(id={self.id}, agent_id={self.agent_id})>"


class SkillModel(Base):
    """技能模型 - Phase 4.3"""
    __tablename__ = "skills"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True, index=True)
    
    trigger_keywords = Column(JSON, default=list)
    implementation = Column(JSON, default=dict)
    
    success_rate = Column(Float, default=0.0)
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Skill(id={self.id}, name={self.name})>"


class AgentSkillModel(Base):
    """Agent-技能关联模型 - Phase 4.3"""
    __tablename__ = "agent_skills"

    agent_id = Column(String, primary_key=True, index=True)
    skill_id = Column(String, primary_key=True, index=True)
    confidence = Column(Float, default=1.0)
    acquired_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_agent_skill", "agent_id", "skill_id"),
    )

    def __repr__(self):
        return f"<AgentSkill(agent_id={self.agent_id}, skill_id={self.skill_id})>"
