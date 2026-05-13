from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Index, Boolean
from sqlalchemy.sql import func
from app.database import Base


class CostRecordDB(Base):
    __tablename__ = "cost_records"

    id = Column(String(36), primary_key=True, index=True)
    agent_id = Column(String(36), nullable=True, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    
    model = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    cost = Column(Float, default=0.0)
    
    latency_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_cost_created_model', 'created_at', 'model'),
        Index('idx_cost_agent_created', 'agent_id', 'created_at'),
        Index('idx_cost_task_created', 'task_id', 'created_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class PromptCacheDB(Base):
    __tablename__ = "prompt_cache"

    id = Column(String(36), primary_key=True, index=True)
    prompt_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    prompt_snapshot = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    
    model = Column(String(100), nullable=False, index=True)
    
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    hit_count = Column(Integer, default=0)
    miss_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_cache_expires', 'expires_at'),
        Index('idx_cache_access', 'access_count', 'last_accessed_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "prompt_hash": self.prompt_hash,
            "prompt_snapshot": self.prompt_snapshot[:100] + "..." if len(self.prompt_snapshot) > 100 else self.prompt_snapshot,
            "response": self.response[:100] + "..." if len(self.response) > 100 else self.response,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count
        }


class BudgetAlertDB(Base):
    __tablename__ = "budget_alerts"

    id = Column(String(36), primary_key=True, index=True)
    alert_name = Column(String(100), nullable=True)
    threshold = Column(Float, nullable=False)
    period = Column(String(20), default="monthly")
    dimension = Column(String(20), default="total")
    is_enabled = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_alert_dimension_period', 'dimension', 'period'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "alert_name": self.alert_name,
            "threshold": self.threshold,
            "period": self.period,
            "dimension": self.dimension,
            "is_enabled": self.is_enabled,
            "is_triggered": self.is_triggered,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
