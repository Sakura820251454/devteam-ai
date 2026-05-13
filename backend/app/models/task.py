from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def sort_value(self) -> int:
        return {"low": 1, "medium": 2, "high": 3, "urgent": 4}[self.value]


class TaskHistory(BaseModel):
    action: str
    actor: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    status: TaskStatus = Field(default=TaskStatus.BACKLOG)
    priority: Priority = Field(default=Priority.MEDIUM)
    assigned_agents: List[str] = Field(default_factory=list)
    collaborated_agents: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    linked_documents: List[str] = Field(default_factory=list)
    created_by: str = "system"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    history: List[TaskHistory] = Field(default_factory=list)

    def get_valid_transitions(self) -> List[TaskStatus]:
        valid_transitions = {
            TaskStatus.BACKLOG: [TaskStatus.TODO, TaskStatus.CANCELLED],
            TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.BACKLOG, TaskStatus.CANCELLED],
            TaskStatus.IN_PROGRESS: [TaskStatus.REVIEW, TaskStatus.PAUSED, TaskStatus.TODO],
            TaskStatus.REVIEW: [TaskStatus.DONE, TaskStatus.IN_PROGRESS],
            TaskStatus.PAUSED: [TaskStatus.IN_PROGRESS, TaskStatus.TODO],
            TaskStatus.DONE: [TaskStatus.REVIEW],
            TaskStatus.CANCELLED: [TaskStatus.BACKLOG],
        }
        return valid_transitions.get(self.status, [])

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        return new_status in self.get_valid_transitions()

    def transition_to(self, new_status: TaskStatus):
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        self.status = new_status
        self.updated_at = datetime.now()
        if new_status == TaskStatus.DONE:
            self.completed_at = datetime.now()

    def add_history(self, action: str, actor: str) -> None:
        self.history.append(TaskHistory(action=action, actor=actor))


class TaskAuditLog(BaseModel):
    id: str
    task_id: str
    action: str
    actor: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
