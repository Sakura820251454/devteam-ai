from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


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
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)
    participants: List[str] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)
    token_budget: int = Field(default=100000)
    token_used: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    
    def add_message(self, message: Message):
        self.messages.append(message)
        self.token_used += len(message.content) // 4
