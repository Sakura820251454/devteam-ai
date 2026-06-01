"""MessageBus 单元测试 — Agent 间消息通信。

覆盖 subscribe / unsubscribe / 发送模式 / history / channel / topic / cleanup。
"""
import pytest
from app.services.collaboration.message_bus import (
    MessageBus, Message, MessageType, MessageChannel,
)


def _make_msg(sender_id="agent-1", sender_name="Agent 1", content="hello",
              recipients=None, channel=None, msg_type=MessageType.TEXT):
    return Message(
        sender_id=sender_id,
        sender_name=sender_name,
        content=content,
        recipients=recipients or [],
        channel=channel or MessageChannel.PUBLIC.value,
        message_type=msg_type,
    )


class TestSubscribe:
    """订阅管理。"""

    def test_subscribe_returns_id(self):
        bus = MessageBus()
        sub_id = bus.subscribe("agent-1", ["public"], lambda m: None)
        assert sub_id is not None
        assert len(sub_id) > 0

    def test_subscribe_multiple_channels(self):
        bus = MessageBus()
        bus.subscribe("agent-1", ["public", "private"], lambda m: None)
        assert "public" in bus._subscribers
        assert "private" in bus._subscribers

    def test_unsubscribe_existing(self):
        bus = MessageBus()
        sub_id = bus.subscribe("agent-1", ["public"], lambda m: None)
        assert bus.unsubscribe(sub_id) is True

    def test_unsubscribe_nonexistent(self):
        bus = MessageBus()
        assert bus.unsubscribe("no-such-id") is False


class TestBroadcast:
    """公共广播。"""

    @pytest.mark.asyncio
    async def test_broadcast_delivers_to_public_subscribers(self):
        bus = MessageBus()
        received = []

        bus.subscribe("agent-2", ["public"], lambda m: received.append(m.content))
        await bus.broadcast(_make_msg(content="全员通知"))

        assert "全员通知" in received

    @pytest.mark.asyncio
    async def test_broadcast_not_delivered_to_private_subscribers(self):
        """广播消息不应投递给只订阅 private 频道的订阅者。"""
        bus = MessageBus()
        received = []

        bus.subscribe("agent-2", ["private"], lambda m: received.append(m.content))
        await bus.broadcast(_make_msg(content="广播"))

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_broadcast_with_async_callback(self):
        bus = MessageBus()
        received = []

        async def async_handler(msg):
            received.append(msg.content)

        bus.subscribe("agent-2", ["public"], async_handler)
        await bus.broadcast(_make_msg(content="异步通知"))

        assert "异步通知" in received

    @pytest.mark.asyncio
    async def test_broadcast_sets_public_channel(self):
        bus = MessageBus()
        msg = _make_msg(content="广播", channel="something-else")
        await bus.broadcast(msg)
        assert msg.channel == MessageChannel.PUBLIC.value

    @pytest.mark.asyncio
    async def test_broadcast_callback_exception_swallowed(self):
        bus = MessageBus()
        good = []

        bus.subscribe("agent-1", ["public"], lambda m: (_ for _ in ()).throw(RuntimeError("boom")))
        bus.subscribe("agent-2", ["public"], lambda m: good.append(True))
        await bus.broadcast(_make_msg())

        assert len(good) == 1

    @pytest.mark.asyncio
    async def test_broadcast_filter_by_sender(self):
        """filter_sender 只接收指定发送者的消息。"""
        bus = MessageBus()
        from_a = []
        from_b = []

        bus.subscribe("agent-x", ["public"], lambda m: from_a.append(m.content), filter_sender="agent-a")
        bus.subscribe("agent-y", ["public"], lambda m: from_b.append(m.content), filter_sender="agent-b")

        await bus.broadcast(_make_msg(sender_id="agent-a", content="来自A"))
        await bus.broadcast(_make_msg(sender_id="agent-b", content="来自B"))

        assert "来自A" in from_a
        assert "来自B" not in from_a
        assert "来自B" in from_b


class TestPrivateMessage:
    """私信。"""

    @pytest.mark.asyncio
    async def test_send_private(self):
        bus = MessageBus()
        received = []

        bus.subscribe("agent-2", ["private"], lambda m: received.append(m.content))
        msg = _make_msg(recipients=["agent-2"])
        await bus.send_private(msg)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_private_requires_exactly_one_recipient(self):
        bus = MessageBus()
        msg = _make_msg(recipients=["agent-2", "agent-3"])
        with pytest.raises(ValueError, match="exactly one recipient"):
            await bus.send_private(msg)

    @pytest.mark.asyncio
    async def test_private_requires_at_least_one_recipient(self):
        bus = MessageBus()
        msg = _make_msg(recipients=[])
        with pytest.raises(ValueError, match="exactly one recipient"):
            await bus.send_private(msg)


class TestGroupMessage:
    """群组消息。"""

    @pytest.mark.asyncio
    async def test_send_group(self):
        bus = MessageBus()
        received = []

        bus.subscribe("agent-2", ["group-1"], lambda m: received.append(m.content))
        bus.subscribe("agent-3", ["group-1"], lambda m: received.append(m.content))
        msg = _make_msg(recipients=["agent-2", "agent-3"], channel="group-1")
        await bus.send_group(msg, "group-1")

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_group_requires_at_least_two(self):
        bus = MessageBus()
        msg = _make_msg(recipients=["agent-2"])
        with pytest.raises(ValueError, match="at least two"):
            await bus.send_group(msg, "group-1")


class TestSendToTask:
    """任务频道消息。"""

    @pytest.mark.asyncio
    async def test_send_to_task(self):
        bus = MessageBus()
        received = []

        bus.subscribe("agent-2", ["task:task-1"], lambda m: received.append(m.content))
        msg = _make_msg(content="任务消息")
        await bus.send_to_task(msg, "task-1")

        assert len(received) == 1
        assert msg.channel == "task:task-1"


class TestHistory:
    """消息历史。"""

    @pytest.mark.asyncio
    async def test_get_history_default_channel(self):
        bus = MessageBus()
        await bus.broadcast(_make_msg(content="msg1"))
        await bus.broadcast(_make_msg(content="msg2"))

        history = bus.get_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_history_with_limit_offset(self):
        bus = MessageBus()
        for i in range(5):
            await bus.broadcast(_make_msg(content=f"msg{i}"))

        page = bus.get_history(limit=2, offset=1)
        assert len(page) == 2

    @pytest.mark.asyncio
    async def test_get_conversation_between(self):
        bus = MessageBus()
        # 用 _deliver_message 保留 recipients（broadcast 会清空 recipients）
        await bus._deliver_message(_make_msg(
            sender_id="alice", recipients=["bob"], content="hi bob",
            channel="private"))
        await bus._deliver_message(_make_msg(
            sender_id="bob", recipients=["alice"], content="hi alice",
            channel="private"))
        await bus._deliver_message(_make_msg(
            sender_id="charlie", recipients=["dave"], content="other",
            channel="private"))

        conv = bus.get_conversation_between("alice", "bob")
        assert len(conv) == 2


class TestChannels:
    """频道管理。"""

    def test_join_and_leave_channel(self):
        bus = MessageBus()
        bus.join_channel("agent-1", "general")
        assert "agent-1" in bus.get_channel_members("general")

        bus.leave_channel("agent-1", "general")
        assert "agent-1" not in bus.get_channel_members("general")

    def test_join_channel_idempotent(self):
        """重复加入同一频道不应重复添加。"""
        bus = MessageBus()
        bus.join_channel("agent-1", "general")
        bus.join_channel("agent-1", "general")
        assert len(bus.get_channel_members("general")) == 1

    def test_get_channel_members_empty(self):
        bus = MessageBus()
        assert bus.get_channel_members("nonexistent") == []


class TestProjectChannels:
    """项目级频道。"""

    @pytest.mark.asyncio
    async def test_send_to_stage(self):
        bus = MessageBus()
        received = []

        channel = bus.get_stage_channel("proj-1", "collect")
        bus.subscribe("agent-1", [channel], lambda m: received.append(m))

        msg = _make_msg(content="阶段消息")
        await bus.send_to_stage(msg, "proj-1", "collect")

        assert len(received) == 1
        assert received[0].metadata.get("stage") == "collect"
        assert received[0].metadata.get("project_id") == "proj-1"

    @pytest.mark.asyncio
    async def test_get_stage_history(self):
        bus = MessageBus()
        msg = _make_msg(content="阶段1消息")
        await bus.send_to_stage(msg, "proj-1", "collect")

        history = bus.get_stage_history("proj-1", "collect")
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_get_stage_context_includes_public(self):
        bus = MessageBus()
        pub_msg = _make_msg(content="公共消息")
        pub_msg.metadata["project_id"] = "proj-1"
        await bus.broadcast(pub_msg)

        stage_msg = _make_msg(content="阶段消息")
        await bus.send_to_stage(stage_msg, "proj-1", "collect")

        ctx = bus.get_stage_context("proj-1", "collect", include_public=True)
        assert len(ctx) >= 1

    def test_get_prerequisite_context(self):
        bus = MessageBus()
        stage_order = ["collect", "analyze", "report"]
        ctx = bus.get_prerequisite_context("proj-1", "analyze", stage_order)
        assert isinstance(ctx, list)

    def test_get_project_channel(self):
        assert "project:abc" == MessageBus.get_project_channel("abc")


class TestTopicSubscription:
    """主题订阅。"""

    @pytest.mark.asyncio
    async def test_topic_matching(self):
        bus = MessageBus()
        received = []

        def handler(msg):
            received.append(msg.content)

        bus.subscribe_to_topics("agent-1", ["urgent", "security"], handler)

        # topic 订阅者在 "topics" channel，消息需路由到此 channel
        msg = _make_msg(content="紧急事件", channel="topics")
        msg.metadata["topic"] = "urgent"
        await bus._deliver_message(msg)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_topic_not_matching(self):
        bus = MessageBus()
        received = []

        bus.subscribe_to_topics("agent-1", ["urgent"], lambda m: received.append(m.content))

        msg = _make_msg(content="普通消息", channel="topics")
        msg.metadata["topic"] = "normal"
        await bus._deliver_message(msg)

        assert len(received) == 0


class TestCleanup:
    """清理。"""

    def test_clear_history(self):
        bus = MessageBus()
        bus._message_history["public"] = [_make_msg()]
        bus.clear_history()
        assert len(bus._message_history["public"]) == 0

    def test_clear_history_specific_channel(self):
        bus = MessageBus()
        bus._message_history["test-chan"] = [_make_msg()]
        bus._message_history["public"] = [_make_msg()]
        bus.clear_history("test-chan")
        assert len(bus._message_history["test-chan"]) == 0
        assert len(bus._message_history.get("public", [])) == 1

    def test_clear_project_history(self):
        bus = MessageBus()
        ch = bus.get_project_channel("proj-1")
        bus._message_history[ch] = [_make_msg()]
        bus.clear_project_history("proj-1")
        assert len(bus.get_history_by_project("proj-1")) == 0

    def test_cleanup_project_channels(self):
        bus = MessageBus()
        bus._message_history["stage:proj-1:collect"] = [_make_msg()]
        bus._message_history["project:proj-1"] = [_make_msg()]
        bus._message_history["stage:proj-2:collect"] = [_make_msg()]

        bus._channel_members["stage:proj-1:collect"] = ["agent-1"]
        bus._channel_members["project:proj-1"] = ["agent-2"]

        bus.cleanup_project_channels("proj-1")

        assert "stage:proj-1:collect" not in bus._message_history
        assert "project:proj-1" not in bus._message_history
        assert "stage:proj-2:collect" in bus._message_history  # 其他项目不受影响
        assert "stage:proj-1:collect" not in bus._channel_members
        assert "project:proj-1" not in bus._channel_members


class TestMessageModel:
    """Message 模型方法。"""

    def test_is_broadcast(self):
        msg = _make_msg(recipients=[], channel="public")
        assert msg.is_broadcast() is True

        msg2 = _make_msg(recipients=["agent-2"], channel="private")
        assert msg2.is_broadcast() is False

    def test_is_private(self):
        msg = _make_msg(recipients=["agent-2"], channel="private")
        assert msg.is_private() is True

        msg2 = _make_msg(recipients=["agent-2", "agent-3"], channel="private")
        assert msg2.is_private() is False

    def test_is_group(self):
        msg = _make_msg(recipients=["agent-2", "agent-3"], channel="group-1")
        assert msg.is_group() is True

        msg2 = _make_msg(recipients=[], channel="public")
        assert msg2.is_group() is False
