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

    # ========== 项目级消息辅助方法 ==========

    @staticmethod
    def get_project_channel(project_id: str) -> str:
        return f"project:{project_id}"

    @staticmethod
    def get_stage_channel(project_id: str, stage_key: str) -> str:
        return f"stage:{project_id}:{stage_key}"

    def get_history_by_project(self, project_id: str) -> List[Message]:
        channel = self.get_project_channel(project_id)
        return self._message_history.get(channel, [])

    def clear_project_history(self, project_id: str) -> None:
        channel = self.get_project_channel(project_id)
        self.clear_history(channel)

    # ========== 阶段级消息 ==========

    async def send_to_stage(self, message: Message, project_id: str, stage_key: str) -> None:
        """发送消息到指定阶段频道"""
        channel = self.get_stage_channel(project_id, stage_key)
        message.channel = channel
        if "stage" not in message.metadata:
            message.metadata["stage"] = stage_key
        if "project_id" not in message.metadata:
            message.metadata["project_id"] = project_id
        await self._deliver_message(message)

    def get_stage_history(
        self,
        project_id: str,
        stage_key: str,
        limit: int = 100,
    ) -> List[Message]:
        """获取指定阶段的消息历史"""
        channel = self.get_stage_channel(project_id, stage_key)
        history = self._message_history.get(channel, [])
        return history[-limit:]

    def get_stage_context(
        self,
        project_id: str,
        stage_key: str,
        include_public: bool = True,
        limit: int = 50,
    ) -> List[Message]:
        """获取阶段的完整上下文（阶段消息 + 可选公共消息）"""
        context = self.get_stage_history(project_id, stage_key, limit=limit)
        if include_public:
            public_msgs = self._message_history.get(MessageChannel.PUBLIC.value, [])
            # 获取与项目相关的公共消息（通过 metadata）
            relevant = [m for m in public_msgs if m.metadata.get("project_id") == project_id]
            context.extend(relevant[-limit:])
        return sorted(context, key=lambda m: m.timestamp)[-limit:]

    def get_prerequisite_context(
        self,
        project_id: str,
        current_stage_key: str,
        stage_order: List[str],
    ) -> List[Message]:
        """
        获取前置阶段的上下文消息（用于可执行反馈）
        stage_order: 按顺序排列的阶段 key 列表
        返回当前阶段之前所有阶段的消息
        """
        context = []
        try:
            current_idx = stage_order.index(current_stage_key)
            prerequisite_keys = stage_order[:current_idx]
        except ValueError:
            prerequisite_keys = stage_order

        for stage_key in prerequisite_keys:
            channel = self.get_stage_channel(project_id, stage_key)
            msgs = self._message_history.get(channel, [])
            context.extend(msgs[-20:])  # 每个阶段取最近 20 条

        # 也包含公共消息
        public_msgs = self._message_history.get(MessageChannel.PUBLIC.value, [])
        relevant_public = [m for m in public_msgs if m.metadata.get("project_id") == project_id]
        context.extend(relevant_public[-30:])

        return sorted(context, key=lambda m: m.timestamp)

    # ========== 主题/标签订阅 ==========

    def subscribe_to_topics(
        self,
        agent_id: str,
        topics: List[str],
        callback: Callable[[Message], None],
    ) -> str:
        """
        按消息主题标签订阅。消息的 metadata.topic 匹配时触发回调。
        """
        subscription_id = str(uuid.uuid4())
        channel = "topics"
        if channel not in self._subscribers:
            self._subscribers[channel] = []

        # 重写 callback 以自动过滤 topic
        async def topic_filtered_callback(message: Message):
            msg_topic = message.metadata.get("topic", "")
            if msg_topic in topics:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)

        self._subscribers[channel].append(Subscription(
            agent_id=agent_id,
            channels=[channel],
            callback=topic_filtered_callback,
        ))
        return subscription_id

    def cleanup_project_channels(self, project_id: str) -> None:
        """清理与项目相关的所有频道"""
        prefix_stage = f"stage:{project_id}:"
        prefix_project = f"project:{project_id}"

        for channel in list(self._message_history.keys()):
            if channel.startswith(prefix_stage) or channel == prefix_project:
                del self._message_history[channel]

        for channel in list(self._channel_members.keys()):
            if channel.startswith(prefix_stage) or channel == prefix_project:
                del self._channel_members[channel]


message_bus = MessageBus()
