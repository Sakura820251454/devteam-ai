from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class SessionPhase(str, Enum):
    """会话阶段状态机：发起 → 协商 → 执行 → 验证 → 归档"""
    INITIATING = "initiating"      # 发起：定义目标、组建团队
    NEGOTIATING = "negotiating"    # 协商：讨论方案、分配任务
    EXECUTING = "executing"        # 执行：Agent 并行执行任务
    VERIFYING = "verifying"        # 验证：审核结果、冲突仲裁
    ARCHIVED = "archived"          # 归档：总结反思、经验沉淀

    def next_phases(self) -> List["SessionPhase"]:
        transitions = {
            SessionPhase.INITIATING: [SessionPhase.NEGOTIATING],
            SessionPhase.NEGOTIATING: [SessionPhase.EXECUTING, SessionPhase.INITIATING],
            SessionPhase.EXECUTING: [SessionPhase.VERIFYING, SessionPhase.NEGOTIATING],
            SessionPhase.VERIFYING: [SessionPhase.ARCHIVED, SessionPhase.EXECUTING],
            SessionPhase.ARCHIVED: [],
        }
        return transitions.get(self, [])

    def can_transition_to(self, target: "SessionPhase") -> bool:
        return target in self.next_phases()


class MessageType(str, Enum):
    TEXT = "text"
    ACTION = "action"
    SYSTEM = "system"


class Message(BaseModel):
    id: str
    session_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: MessageType = Field(default=MessageType.TEXT)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class Session(BaseModel):
    id: str
    title: str = Field(default="新会话")
    project_id: Optional[str] = None
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)
    phase: SessionPhase = Field(default=SessionPhase.INITIATING)
    participants: List[str] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)
    token_budget: int = Field(default=100000)
    token_used: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None

    def add_message(self, message: Message):
        self.messages.append(message)
        self.token_used += len(message.content) // 4

    def transition_phase(self, target: SessionPhase) -> bool:
        if not self.phase.can_transition_to(target):
            return False
        self.phase = target
        return True
