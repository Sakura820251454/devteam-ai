from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, JSON, Index
from datetime import datetime
from app.database import Base


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="planning", index=True)
    current_phase = Column(String, default="requirement")
    requirements = Column(Text, default="")
    team_config = Column(JSON, default=dict)
    settings = Column(JSON, default=dict)
    created_by = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_project_status", "status"),
    )

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="backlog", index=True)
    priority = Column(String, default="medium")
    risk_level = Column(String, default="low")
    assigned_agents = Column(JSON, default=list)
    collaborated_agents = Column(JSON, default=list)
    dependencies = Column(JSON, default=list)
    linked_documents = Column(JSON, default=list)
    created_by = Column(String, default="system")
    tags = Column(JSON, default=list)
    history = Column(JSON, default=list)
    approval_required = Column(Boolean, default=False)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_task_project_status", "project_id", "status"),
    )

    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"


class PipelineModel(Base):
    __tablename__ = "pipelines"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="idle", index=True)
    current_stage = Column(String, default="requirement_analysis")
    progress = Column(Float, default=0.0)
    agents = Column(JSON, default=list)
    task_ids = Column(JSON, default=list)
    context = Column(JSON, default=dict)
    logs = Column(JSON, default=list)
    team_config = Column(JSON, default=dict)
    agent_roles = Column(JSON, default=dict)
    stages = Column(JSON, default=list)
    paused = Column(Boolean, default=False)
    stop_requested = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_pipeline_project", "project_id"),
        Index("idx_pipeline_status", "status"),
    )

    def __repr__(self):
        return f"<Pipeline(id={self.id}, name={self.name}, status={self.status})>"


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New Session")
    project_id = Column(String, nullable=True, index=True)
    status = Column(String, default="active", index=True)
    phase = Column(String, default="initiating")
    participants = Column(JSON, default=list)
    token_budget = Column(Integer, default=100000)
    token_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    ended_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Session(id={self.id}, title={self.title}, status={self.status})>"


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    sender_id = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text")
    metadata_json = Column("metadata", JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index("idx_message_session_time", "session_id", "timestamp"),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, sender={self.sender_name}, session={self.session_id})>"
