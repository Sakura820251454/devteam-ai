import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass, field


class MessageType(str, Enum):
    TEXT = "text"
    ACTION = "action"
    SYSTEM = "system"


class MessageChannel(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    TASK = "task"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    sender_name: str
    recipients: List[str] = Field(default_factory=list)
    channel: str = MessageChannel.PUBLIC.value
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_broadcast(self) -> bool:
        return len(self.recipients) == 0 and self.channel == MessageChannel.PUBLIC.value

    def is_private(self) -> bool:
        return self.channel == MessageChannel.PRIVATE.value and len(self.recipients) == 1

    def is_group(self) -> bool:
        return self.channel != MessageChannel.PUBLIC.value and len(self.recipients) > 1


@dataclass
class Subscription:
    agent_id: str
    channels: List[str]
    callback: Callable[[Message], None]
    filter_sender: Optional[str] = None


class MessageBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Subscription]] = {}
        self._message_history: Dict[str, List[Message]] = {
            MessageChannel.PUBLIC.value: []
        }
        self._channel_members: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        agent_id: str,
        channels: List[str],
        callback: Callable[[Message], None],
        filter_sender: Optional[str] = None
    ) -> str:
        subscription_id = str(uuid.uuid4())
        for channel in channels:
            if channel not in self._subscribers:
                self._subscribers[channel] = []
            self._subscribers[channel].append(Subscription(
                agent_id=agent_id,
                channels=channels,
                callback=callback,
                filter_sender=filter_sender
            ))
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        for channel_subs in self._subscribers.values():
            for i, sub in enumerate(channel_subs):
                if f"{sub.agent_id}:{sub.callback}" == subscription_id:
                    channel_subs.pop(i)
                    return True
        return False

    async def broadcast(self, message: Message) -> None:
        message.channel = MessageChannel.PUBLIC.value
        message.recipients = []
        await self._deliver_message(message)

    async def send_private(self, message: Message) -> None:
        message.channel = MessageChannel.PRIVATE.value
        if len(message.recipients) != 1:
            raise ValueError("Private message must have exactly one recipient")
        await self._deliver_message(message)

    async def send_group(self, message: Message, group_id: str) -> None:
        message.channel = group_id
        if len(message.recipients) < 2:
            raise ValueError("Group message must have at least two recipients")
        await self._deliver_message(message)

    async def send_to_task(self, message: Message, task_id: str) -> None:
        channel = f"task:{task_id}"
        message.channel = channel
        await self._deliver_message(message)

    async def _deliver_message(self, message: Message) -> None:
        async with self._lock:
            self._history_add(message)

        target_channels = self._get_target_channels(message)

        for channel in target_channels:
            if channel in self._subscribers:
                for subscription in self._subscribers[channel]:
                    if self._should_deliver(subscription, message):
                        try:
                            if asyncio.iscoroutinefunction(subscription.callback):
                                await subscription.callback(message)
                            else:
                                subscription.callback(message)
                        except Exception as e:
                            print(f"Error delivering message to {subscription.agent_id}: {e}")

    def _get_target_channels(self, message: Message) -> List[str]:
        channels = []
        if message.is_broadcast():
            channels.append(MessageChannel.PUBLIC.value)
        else:
            if message.channel:
                channels.append(message.channel)
        return channels

    def _should_deliver(self, subscription: Subscription, message: Message) -> bool:
        if subscription.filter_sender and message.sender_id != subscription.filter_sender:
            return False
        return True

    def _history_add(self, message: Message) -> None:
        channel = message.channel if message.channel else MessageChannel.PUBLIC.value
        if channel not in self._message_history:
            self._message_history[channel] = []
        self._message_history[channel].append(message)

    def get_history(
        self,
        channel: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        target_channel = channel or MessageChannel.PUBLIC.value
        history = self._message_history.get(target_channel, [])
        return history[offset:offset + limit]

    def get_conversation_between(
        self,
        agent1_id: str,
        agent2_id: str,
        limit: int = 50
    ) -> List[Message]:
        all_messages = self._message_history.get(MessageChannel.PUBLIC.value, [])
        private_channels = [
            ch for ch in self._message_history.keys()
            if ch != MessageChannel.PUBLIC.value
        ]
        for ch in private_channels:
            all_messages.extend(self._message_history[ch])

        filtered = [
            msg for msg in all_messages
            if (msg.sender_id in [agent1_id, agent2_id] and
                agent1_id in msg.recipients or agent2_id in msg.recipients)
        ]
        return sorted(filtered, key=lambda m: m.timestamp, reverse=True)[:limit]

    def join_channel(self, agent_id: str, channel: str) -> None:
        if channel not in self._channel_members:
            self._channel_members[channel] = []
        if agent_id not in self._channel_members[channel]:
            self._channel_members[channel].append(agent_id)

    def leave_channel(self, agent_id: str, channel: str) -> None:
        if channel in self._channel_members:
            if agent_id in self._channel_members[channel]:
                self._channel_members[channel].remove(agent_id)

    def get_channel_members(self, channel: str) -> List[str]:
        return self._channel_members.get(channel, [])

    def clear_history(self, channel: Optional[str] = None) -> None:
        if channel:
            self._message_history[channel] = []
        else:
            self._message_history = {MessageChannel.PUBLIC.value: []}


message_bus = MessageBus()
