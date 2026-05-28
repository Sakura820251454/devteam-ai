"""测试工厂方法。

提供快速构建测试对象的工厂函数，减少测试代码中的样板设置。
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from app.services.collaboration.pipeline_orchestrator import (
    Pipeline,
    PipelineStatus,
    PipelineOrchestrator,
)
from app.models.task import Task, TaskStatus, Priority, RiskLevel


class PipelineFactory:
    """Pipeline 对象工厂。"""

    @staticmethod
    def create(
        id: str = "factory-pipeline-001",
        project_id: str = "factory-project-001",
        name: str = "测试流水线",
        status: PipelineStatus = PipelineStatus.IDLE,
        agents: Optional[List[str]] = None,
        stages: Optional[List[Dict[str, Any]]] = None,
        task_ids: Optional[List[str]] = None,
        progress: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> Pipeline:
        p = Pipeline()
        p.id = id
        p.project_id = project_id
        p.name = name
        p.status = status
        p.agents = agents or []
        p.stages = stages or []
        p.task_ids = task_ids or []
        p.progress = progress
        p.context = context or {}
        return p

    @staticmethod
    def idle(**kwargs) -> Pipeline:
        return PipelineFactory.create(status=PipelineStatus.IDLE, **kwargs)

    @staticmethod
    def running(**kwargs) -> Pipeline:
        return PipelineFactory.create(status=PipelineStatus.RUNNING, **kwargs)

    @staticmethod
    def paused(**kwargs) -> Pipeline:
        return PipelineFactory.create(status=PipelineStatus.PAUSED, **kwargs)

    @staticmethod
    def completed(**kwargs) -> Pipeline:
        return PipelineFactory.create(status=PipelineStatus.COMPLETED, **kwargs)

    @staticmethod
    def failed(**kwargs) -> Pipeline:
        return PipelineFactory.create(status=PipelineStatus.FAILED, **kwargs)


class TaskFactory:
    """Task 对象工厂。"""

    _id_counter = 0

    @classmethod
    def _next_id(cls) -> str:
        cls._id_counter += 1
        return f"factory-task-{cls._id_counter:03d}"

    @classmethod
    def create(
        cls,
        id: Optional[str] = None,
        title: str = "测试任务",
        description: str = "这是一个测试任务",
        project_id: str = "factory-project-001",
        status: TaskStatus = TaskStatus.BACKLOG,
        priority: Priority = Priority.MEDIUM,
        risk_level: RiskLevel = RiskLevel.LOW,
        tags: Optional[List[str]] = None,
        assigned_agents: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Task:
        return Task(
            id=id or cls._next_id(),
            title=title,
            description=description,
            project_id=project_id,
            status=status,
            priority=priority,
            risk_level=risk_level,
            tags=tags or [],
            assigned_agents=assigned_agents or [],
            dependencies=dependencies or [],
        )

    @classmethod
    def todo(cls, **kwargs) -> Task:
        return cls.create(status=TaskStatus.TODO, **kwargs)

    @classmethod
    def in_progress(cls, **kwargs) -> Task:
        return cls.create(status=TaskStatus.IN_PROGRESS, **kwargs)

    @classmethod
    def done(cls, **kwargs) -> Task:
        return cls.create(status=TaskStatus.DONE, **kwargs)
