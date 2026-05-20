from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Index
from datetime import datetime
from app.database import Base


class TaskExecutionModel(Base):
    """任务执行状态持久化模型"""
    __tablename__ = "task_executions"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False)
    project_id = Column(String, nullable=True, index=True)

    status = Column(String, default="idle")
    current_step_index = Column(Integer, default=0)
    total_steps = Column(Integer, default=1)

    last_heartbeat_at = Column(DateTime, nullable=True)
    heartbeat_count = Column(Integer, default=0)

    accumulated_result = Column(Text, nullable=True)
    checkpoint_data = Column(JSON, default=dict)

    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_execution_task_id", "task_id"),
        Index("idx_execution_status", "status"),
        Index("idx_execution_project_id", "project_id"),
    )

    def __repr__(self):
        return f"<TaskExecution(id={self.id}, task_id={self.task_id}, status={self.status})>"


class TaskCheckpointModel(Base):
    """任务检查点持久化模型"""
    __tablename__ = "task_checkpoints"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=True, index=True)
    step_index = Column(Integer, nullable=False)

    step_name = Column(String, nullable=True)
    context = Column(JSON, default=dict)
    partial_result = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_checkpoint_task_step", "task_id", "step_index"),
        Index("idx_checkpoint_project_id", "project_id"),
    )

    def __repr__(self):
        return f"<TaskCheckpoint(id={self.id}, task_id={self.task_id}, step={self.step_index})>"
