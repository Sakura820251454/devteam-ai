"""SpeakingController 单元测试 — 发言控制、Token 预算、速率限制。

覆盖 TokenBudget / 发言模式 / rate limit / 队列管理 / 会话清理。
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.collaboration.speaking_controller import (
    SpeakingController, SpeakingMode, SpeakingTurn, TokenBudget, AgentSpeakingConfig,
)


class TestTokenBudget:
    """Token 预算模型。"""

    def test_remaining(self):
        budget = TokenBudget(session_id="s1", total_budget=1000, used_tokens=300)
        assert budget.remaining() == 700

    def test_usage_ratio(self):
        budget = TokenBudget(session_id="s1", total_budget=1000, used_tokens=500)
        assert budget.usage_ratio() == 0.5

    def test_usage_ratio_zero_budget(self):
        budget = TokenBudget(session_id="s1", total_budget=0)
        assert budget.usage_ratio() == 0

    def test_is_exhausted(self):
        budget = TokenBudget(session_id="s1", total_budget=100, used_tokens=100)
        assert budget.is_exhausted() is True

        budget2 = TokenBudget(session_id="s2", total_budget=100, used_tokens=99)
        assert budget2.is_exhausted() is False

    def test_is_warning(self):
        budget = TokenBudget(session_id="s1", total_budget=1000, used_tokens=850, warning_threshold=0.8)
        assert budget.is_warning() is True

        budget2 = TokenBudget(session_id="s2", total_budget=1000, used_tokens=700, warning_threshold=0.8)
        assert budget2.is_warning() is False

    def test_used_tokens_capped(self):
        """consume_tokens 不应超过 total_budget。"""
        budget = TokenBudget(session_id="s1", total_budget=100, used_tokens=90)
        ctrl = SpeakingController()
        ctrl._token_budgets["s1"] = budget
        result = ctrl.consume_tokens("s1", 50)
        assert result is True
        assert budget.used_tokens == 100


class TestMode:
    """发言模式。"""

    def test_default_mode(self):
        ctrl = SpeakingController()
        assert ctrl.get_mode("any") == SpeakingMode.FREE_STYLE

    def test_set_and_get_mode(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.ROUND_ROBIN)
        assert ctrl.get_mode("s1") == SpeakingMode.ROUND_ROBIN

    def test_round_robin_initializes_queue(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.ROUND_ROBIN)
        assert ctrl.get_queue_length("s1") == 0  # 队列已初始化


class TestTokenBudgetManagement:
    """Token 预算管理。"""

    def test_set_token_budget(self):
        ctrl = SpeakingController()
        budget = ctrl.set_token_budget("s1", 5000)
        assert budget.total_budget == 5000
        assert budget.session_id == "s1"

    def test_get_token_budget_nonexistent(self):
        ctrl = SpeakingController()
        assert ctrl.get_token_budget("no-session") is None

    def test_get_remaining_tokens(self):
        ctrl = SpeakingController()
        ctrl.set_token_budget("s1", 1000)
        ctrl.consume_tokens("s1", 200)
        assert ctrl.get_remaining_tokens("s1") == 800

    def test_get_remaining_tokens_no_budget(self):
        ctrl = SpeakingController()
        assert ctrl.get_remaining_tokens("no-budget") == -1

    def test_consume_tokens_exhausted(self):
        ctrl = SpeakingController()
        ctrl.set_token_budget("s1", 100)
        ctrl.consume_tokens("s1", 100)
        assert ctrl.consume_tokens("s1", 1) is False


class TestAgentConfig:
    """Agent 发言配置。"""

    def test_set_and_get_config(self):
        ctrl = SpeakingController()
        config = AgentSpeakingConfig(agent_id="agent-1", max_messages_per_minute=5)
        ctrl.set_agent_config("agent-1", config)
        assert ctrl.get_agent_config("agent-1").max_messages_per_minute == 5

    def test_get_config_nonexistent(self):
        ctrl = SpeakingController()
        assert ctrl.get_agent_config("ghost") is None


class TestRequestSpeak:
    """发言请求（4 种模式）。"""

    @pytest.mark.asyncio
    async def test_free_style_immediate(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.FREE_STYLE)
        turn = await ctrl.request_speak("s1", "agent-1", "Agent 1")
        assert turn is not None
        assert turn.agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_sequential_queues(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.SEQUENTIAL)
        await ctrl.request_speak("s1", "agent-1", "A")
        await ctrl.request_speak("s1", "agent-2", "B")
        assert ctrl.get_queue_length("s1") == 2

    @pytest.mark.asyncio
    async def test_round_robin_notifies_first_only(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.ROUND_ROBIN)
        notified = []

        ctrl.register_turn_handler("s1", lambda t: notified.append(t.agent_id))
        await ctrl.request_speak("s1", "agent-1", "A")
        await ctrl.request_speak("s1", "agent-2", "B")
        # ROUND_ROBIN: 只有第一个入队的被通知
        assert len(notified) == 1
        assert notified[0] == "agent-1"

    @pytest.mark.asyncio
    async def test_priority_based_sorts(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.PRIORITY_BASED)
        await ctrl.request_speak("s1", "agent-low", "Low", priority=1)
        await ctrl.request_speak("s1", "agent-high", "High", priority=10)

        # 高优先级应排前面
        queue = ctrl.get_queue("s1")
        assert queue[0].agent_id == "agent-high"

    @pytest.mark.asyncio
    async def test_rate_limit_blocked(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.FREE_STYLE)
        config = AgentSpeakingConfig(agent_id="agent-1", max_messages_per_minute=0)
        ctrl.set_agent_config("agent-1", config)

        turn = await ctrl.request_speak("s1", "agent-1", "A")
        assert turn is None  # 被限速

    @pytest.mark.asyncio
    async def test_rate_limit_allowed_within_window(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.FREE_STYLE)
        config = AgentSpeakingConfig(agent_id="agent-1", max_messages_per_minute=10)
        ctrl.set_agent_config("agent-1", config)

        turn = await ctrl.request_speak("s1", "agent-1", "A")
        assert turn is not None


class TestNextTurn:
    """next_turn 队列出队。"""

    @pytest.mark.asyncio
    async def test_sequential_pop(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.SEQUENTIAL)
        await ctrl.request_speak("s1", "agent-1", "A")
        await ctrl.request_speak("s1", "agent-2", "B")

        turn = await ctrl.next_turn("s1")
        assert turn.agent_id == "agent-1"
        assert ctrl.get_queue_length("s1") == 1

    @pytest.mark.asyncio
    async def test_empty_queue_returns_none(self):
        ctrl = SpeakingController()
        assert await ctrl.next_turn("empty") is None

    @pytest.mark.asyncio
    async def test_priority_queue_pop(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.PRIORITY_BASED)
        await ctrl.request_speak("s1", "agent-low", "L", priority=1)
        await ctrl.request_speak("s1", "agent-high", "H", priority=10)

        turn = await ctrl.next_turn("s1")
        assert turn.agent_id == "agent-high"


class TestSkipTurn:
    """跳过发言。"""

    @pytest.mark.asyncio
    async def test_skip_existing_turn(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.SEQUENTIAL)
        turn = await ctrl.request_speak("s1", "agent-1", "A")

        assert await ctrl.skip_turn("s1", turn.id) is True
        assert ctrl.get_queue_length("s1") == 0

    @pytest.mark.asyncio
    async def test_skip_nonexistent_turn(self):
        ctrl = SpeakingController()
        assert await ctrl.skip_turn("s1", "no-such-turn") is False


class TestClearQueue:
    """清空队列。"""

    @pytest.mark.asyncio
    async def test_clear_queue_returns_count(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.SEQUENTIAL)
        await ctrl.request_speak("s1", "a1", "A")
        await ctrl.request_speak("s1", "a2", "B")

        count = await ctrl.clear_queue("s1")
        assert count == 2
        assert ctrl.get_queue_length("s1") == 0


class TestCurrentSpeaker:
    """当前发言者管理。"""

    def test_set_and_get_current_speaker(self):
        ctrl = SpeakingController()
        ctrl.set_current_speaker("s1", "agent-1")
        assert ctrl.is_speaking("s1") is True
        assert ctrl.get_current_speaker("s1") == "agent-1"

    def test_force_stop_speaking(self):
        ctrl = SpeakingController()
        ctrl.set_current_speaker("s1", "agent-1")
        ctrl.force_stop_speaking("s1")
        assert ctrl.is_speaking("s1") is False

    def test_is_speaking_empty_session(self):
        ctrl = SpeakingController()
        assert ctrl.is_speaking("no-session") is False


class TestTurnHandlers:
    """发言回调注册。"""

    @pytest.mark.asyncio
    async def test_register_and_notify(self):
        ctrl = SpeakingController()
        notified = []

        ctrl.register_turn_handler("s1", lambda t: notified.append(t.agent_id))
        # ROUND_ROBIN 模式：第一个入队的会触发 _notify_turn
        ctrl.set_mode("s1", SpeakingMode.ROUND_ROBIN)
        await ctrl.request_speak("s1", "agent-1", "A")

        assert len(notified) == 1
        assert notified[0] == "agent-1"

    def test_unregister_handler(self):
        ctrl = SpeakingController()
        handler = lambda t: None
        ctrl.register_turn_handler("s1", handler)
        ctrl.unregister_turn_handler("s1", handler)
        assert len(ctrl._turn_handlers.get("s1", [])) == 0


class TestCleanup:
    """会话清理。"""

    def test_cleanup_session(self):
        ctrl = SpeakingController()
        ctrl.set_mode("s1", SpeakingMode.SEQUENTIAL)
        ctrl.set_token_budget("s1", 1000)
        ctrl.set_current_speaker("s1", "agent-1")

        ctrl.cleanup_session("s1")

        assert ctrl.get_mode("s1") == SpeakingMode.FREE_STYLE  # 默认值
        assert ctrl.get_token_budget("s1") is None
        assert ctrl.is_speaking("s1") is False

    def test_cleanup_project_sessions(self):
        ctrl = SpeakingController()
        ctrl.set_mode("project:proj-1:s1", SpeakingMode.SEQUENTIAL)
        ctrl.set_mode("project:proj-2:s1", SpeakingMode.SEQUENTIAL)

        ctrl.cleanup_project_sessions("proj-1")

        assert ctrl.get_mode("project:proj-1:s1") == SpeakingMode.FREE_STYLE
        assert ctrl.get_mode("project:proj-2:s1") == SpeakingMode.SEQUENTIAL  # 其他项目不变
