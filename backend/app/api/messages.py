from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.collaboration.message_bus import Message, MessageType, message_bus


router = APIRouter(prefix="/api/messages", tags=["消息总线"])


class SendMessageRequest(BaseModel):
    sender_id: str
    sender_name: str
    recipients: List[str] = Field(default_factory=list)
    channel: str = "public"
    content: str
    message_type: MessageType = MessageType.TEXT
    metadata: dict = Field(default_factory=dict)


class SendPrivateRequest(BaseModel):
    sender_id: str
    sender_name: str
    recipient_id: str
    content: str
    message_type: MessageType = MessageType.TEXT


class SendGroupRequest(BaseModel):
    sender_id: str
    sender_name: str
    group_id: str
    recipients: List[str]
    content: str
    message_type: MessageType = MessageType.TEXT


class SendTaskMessageRequest(BaseModel):
    sender_id: str
    sender_name: str
    task_id: str
    content: str
    message_type: MessageType = MessageType.TEXT


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    recipients: List[str]
    channel: str
    content: str
    message_type: MessageType
    timestamp: str
    metadata: dict


@router.post("/broadcast", response_model=MessageResponse)
async def send_broadcast(request: SendMessageRequest):
    message = Message(
        sender_id=request.sender_id,
        sender_name=request.sender_name,
        recipients=[],
        channel="public",
        content=request.content,
        message_type=request.message_type,
        metadata=request.metadata
    )
    await message_bus.broadcast(message)
    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        recipients=message.recipients,
        channel=message.channel,
        content=message.content,
        message_type=message.message_type,
        timestamp=message.timestamp.isoformat(),
        metadata=message.metadata
    )


@router.post("/private", response_model=MessageResponse)
async def send_private(request: SendPrivateRequest):
    message = Message(
        sender_id=request.sender_id,
        sender_name=request.sender_name,
        recipients=[request.recipient_id],
        channel="private",
        content=request.content,
        message_type=request.message_type
    )
    await message_bus.send_private(message)
    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        recipients=message.recipients,
        channel=message.channel,
        content=message.content,
        message_type=message.message_type,
        timestamp=message.timestamp.isoformat(),
        metadata=message.metadata
    )


@router.post("/group", response_model=MessageResponse)
async def send_group(request: SendGroupRequest):
    message = Message(
        sender_id=request.sender_id,
        sender_name=request.sender_name,
        recipients=request.recipients,
        channel=request.group_id,
        content=request.content,
        message_type=request.message_type
    )
    await message_bus.send_group(message, request.group_id)
    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        recipients=message.recipients,
        channel=message.channel,
        content=message.content,
        message_type=message.message_type,
        timestamp=message.timestamp.isoformat(),
        metadata=message.metadata
    )


@router.post("/task/{task_id}", response_model=MessageResponse)
async def send_to_task(task_id: str, request: SendTaskMessageRequest):
    message = Message(
        sender_id=request.sender_id,
        sender_name=request.sender_name,
        recipients=[],
        channel=f"task:{task_id}",
        content=request.content,
        message_type=request.message_type
    )
    await message_bus.send_to_task(message, task_id)
    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        recipients=message.recipients,
        channel=message.channel,
        content=message.content,
        message_type=message.message_type,
        timestamp=message.timestamp.isoformat(),
        metadata=message.metadata
    )


@router.get("/history", response_model=List[MessageResponse])
async def get_history(
    channel: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    messages = message_bus.get_history(channel, limit, offset)
    return [
        MessageResponse(
            id=msg.id,
            sender_id=msg.sender_id,
            sender_name=msg.sender_name,
            recipients=msg.recipients,
            channel=msg.channel,
            content=msg.content,
            message_type=msg.message_type,
            timestamp=msg.timestamp.isoformat(),
            metadata=msg.metadata
        )
        for msg in messages
    ]


@router.get("/conversation/{agent1_id}/{agent2_id}", response_model=List[MessageResponse])
async def get_conversation(agent1_id: str, agent2_id: str, limit: int = 50):
    messages = message_bus.get_conversation_between(agent1_id, agent2_id, limit)
    return [
        MessageResponse(
            id=msg.id,
            sender_id=msg.sender_id,
            sender_name=msg.sender_name,
            recipients=msg.recipients,
            channel=msg.channel,
            content=msg.content,
            message_type=msg.message_type,
            timestamp=msg.timestamp.isoformat(),
            metadata=msg.metadata
        )
        for msg in messages
    ]


@router.get("/channel/{channel}/members")
async def get_channel_members(channel: str):
    members = message_bus.get_channel_members(channel)
    return {"channel": channel, "members": members}


@router.post("/channel/{channel}/join")
async def join_channel(channel: str, agent_id: str):
    message_bus.join_channel(agent_id, channel)
    return {"status": "ok", "channel": channel, "agent_id": agent_id}


@router.post("/channel/{channel}/leave")
async def leave_channel(channel: str, agent_id: str):
    message_bus.leave_channel(agent_id, channel)
    return {"status": "ok", "channel": channel, "agent_id": agent_id}
