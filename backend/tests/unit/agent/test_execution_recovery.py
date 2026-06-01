"""
Unit tests for execution recovery system.

Covers: provider timeout, cancellation_token, step planning/parsing,
heartbeat, pause/cancel, execution status, checkpoint flow.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime

from app.core.llm import Message as LLMMessage, LLMResponse
from app.core.llm_providers import BaseLLMProvider
from app.services.agent.agent_executor import (
    AgentExecutor,
    ExecutionStatus,
)
from app.models.task import Task, TaskStatus, Priority


# ============================================================
# Provider-level timeout & cancellation tests
# ============================================================

class TestProviderTimeout:
    """Test that timeout is properly propagated and enforced in providers."""

    @pytest.mark.asyncio
    async def test_chat_passes_timeout_to_provider(self):
        """Provider.chat() should receive and use the timeout parameter."""
        from app.core.llm_providers import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key", base_url="https://test.example.com")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {},
            "model": "gpt-4o-mini"
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client_post = AsyncMock(return_value=mock_resp)

        with patch.object(provider.client, 'post', mock_client_post):
            result = await provider.chat(
                [LLMMessage(role="user", content="hi")],
                timeout=30.0
            )
            assert result.content == "ok"

    @pytest.mark.asyncio
    async def test_chat_raises_on_timeout(self):
        """Provider.chat() should raise TimeoutError when timeout is exceeded."""
        from app.core.llm_providers import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key", base_url="https://test.example.com")

        async def slow_response(*args, **kwargs):
            await asyncio.sleep(999)
            return MagicMock()

        with patch.object(provider.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = slow_response

            with pytest.raises(TimeoutError):
                await provider.chat(
                    [LLMMessage(role="user", content="hi")],
                    timeout=0.01
                )

    @pytest.mark.asyncio
    async def test_chat_checks_cancellation_token(self):
        """Provider.chat() should raise CancelledError when token is set."""
        from app.core.llm_providers import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key", base_url="https://test.example.com")
        cancellation_token = asyncio.Event()
        cancellation_token.set()

        mock_response_data = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {},
            "model": "gpt-4o-mini"
        }

        with patch.object(provider.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.json.return_value = mock_response_data
            mock_post.return_value.raise_for_status = MagicMock()

            with pytest.raises(asyncio.CancelledError):
                await provider.chat(
                    [LLMMessage(role="user", content="hi")],
                    cancellation_token=cancellation_token
                )

    @pytest.mark.asyncio
    async def test_stream_chat_checks_cancellation_mid_stream(self):
        """Provider.stream_chat() should check cancellation token between chunks."""
        from app.core.llm_providers import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key", base_url="https://test.example.com")
        cancellation_token = asyncio.Event()

        lines = [
            'data: {"choices":[{"delta":{"content":"hello"}}]}',
            'data: {"choices":[{"delta":{"content":" world"}}]}',
            'data: [DONE]',
        ]

        async def mock_aiter_lines():
            for i, line in enumerate(lines):
                if i == 1:
                    cancellation_token.set()
                yield line

        mock_response = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider.client, 'stream', return_value=MagicMock()) as mock_stream:
            mock_stream.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream.return_value.__aexit__ = AsyncMock(return_value=None)

            chunks = []
            with pytest.raises(asyncio.CancelledError):
                async for chunk in provider.stream_chat(
                    [LLMMessage(role="user", content="hi")],
                    cancellation_token=cancellation_token
                ):
                    chunks.append(chunk)


# ============================================================
# Step planning & parsing tests
# ============================================================

class TestStepPlanning:
    """Test _plan_task_steps and _parse_steps_from_response."""

    def setup_method(self):
        self.executor = AgentExecutor()

    def test_parse_valid_json_steps(self):
        """Should parse valid JSON with steps array."""
        response = '''```json
{
  "steps": [
    {"name": "分析需求", "description": "分析用户需求", "expected_output": "需求文档"},
    {"name": "设计架构", "description": "设计系统架构", "expected_output": "架构图"},
    {"name": "编写代码", "description": "实现功能", "expected_output": "代码文件"}
  ]
}
```'''
        steps = self.executor._parse_steps_from_response(response)
        assert len(steps) == 3
        assert steps[0]["name"] == "分析需求"
        assert steps[1]["name"] == "设计架构"
        assert steps[2]["name"] == "编写代码"

    def test_parse_plain_json_steps(self):
        """Should parse JSON without markdown code block."""
        response = '{"steps": [{"name": "Step 1"}, {"name": "Step 2"}]}'
        steps = self.executor._parse_steps_from_response(response)
        assert len(steps) == 2
        assert steps[0]["name"] == "Step 1"

    def test_parse_numbered_list_fallback(self):
        """Should fall back to parsing numbered list if JSON fails."""
        response = """1. 第一步：创建数据库模型
2. 第二步：实现API接口
3. 第三步：编写单元测试"""
        steps = self.executor._parse_steps_from_response(response)
        assert len(steps) == 3
        assert "创建数据库模型" in steps[0]["name"]
        assert "实现API接口" in steps[1]["name"]
        assert "编写单元测试" in steps[2]["name"]

    def test_parse_empty_response_returns_empty(self):
        """Should return empty list for unparseable response."""
        steps = self.executor._parse_steps_from_response("")
        assert steps == []

    def test_parse_garbled_response_returns_empty(self):
        """Should return empty list for garbled response."""
        steps = self.executor._parse_steps_from_response("这不是一个有效的JSON或列表格式")
        assert steps == []

    def test_build_step_prompt_without_previous(self):
        """First step prompt should not mention previous work."""
        task = Task(id="t1", title="Test Task", description="Do something")
        step = {"name": "分析需求", "description": "分析用户需求", "expected_output": "需求文档"}
        prompt = self.executor._build_step_prompt(task, step, "", 0, 3)
        assert "第 1/3 步" in prompt
        assert "这是第一个步骤" in prompt
        assert "前序步骤已完成" not in prompt

    def test_build_step_prompt_with_previous(self):
        """Later step prompt should include previous results."""
        task = Task(id="t1", title="Test Task", description="Do something")
        step = {"name": "设计架构", "description": "设计系统架构", "expected_output": "架构图"}
        accumulated = "## 步骤 1: 分析需求\n已完成需求分析"
        prompt = self.executor._build_step_prompt(task, step, accumulated, 1, 3)
        assert "第 2/3 步" in prompt
        assert "前序步骤已完成" in prompt
        assert "已完成需求分析" in prompt
        assert "不要重复已完成的内容" in prompt


# ============================================================
# Step planning integration with mocked LLM
# ============================================================

class TestStepPlanningWithLLM:
    """Test step planning with a mocked LLM service."""

    def setup_method(self):
        self.executor = AgentExecutor()

    @pytest.mark.asyncio
    async def test_plan_task_steps_success(self):
        """Should return steps when LLM returns valid JSON."""
        task = Task(id="t1", title="实现用户登录", description="实现完整的用户登录功能")
        agent = {"id": "agent1", "name": "Developer", "system_prompt": "You are a developer."}

        mock_response = LLMResponse(
            content='{"steps": [{"name": "创建数据模型", "description": "...", "expected_output": "..."}, {"name": "实现API", "description": "...", "expected_output": "..."}]}',
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            model="test-model",
            finish_reason="stop"
        )

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            steps = await self.executor._plan_task_steps(task, agent)
            assert len(steps) == 2
            assert steps[0]["name"] == "创建数据模型"

    @pytest.mark.asyncio
    async def test_plan_task_steps_llm_failure_returns_empty(self):
        """Should return empty list when LLM call fails."""
        task = Task(id="t1", title="Test", description="Test")
        agent = {"id": "agent1", "name": "Dev"}

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = Exception("LLM unavailable")
            steps = await self.executor._plan_task_steps(task, agent)
            assert steps == []

    @pytest.mark.asyncio
    async def test_plan_task_steps_unparseable_response_returns_empty(self):
        """Should return empty list when LLM returns non-JSON."""
        task = Task(id="t1", title="Test", description="Test")
        agent = {"id": "agent1", "name": "Dev"}

        mock_response = LLMResponse(
            content="I think the steps should be... <random text>",
            usage={},
            model="test",
            finish_reason="stop"
        )

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            steps = await self.executor._plan_task_steps(task, agent)
            assert steps == []


# ============================================================
# Heartbeat tests
# ============================================================

class TestHeartbeat:
    """Test heartbeat mechanism."""

    def setup_method(self):
        self.executor = AgentExecutor()

    def test_send_heartbeat_updates_timestamp(self):
        """_send_heartbeat should update last_heartbeat."""
        self.executor._running_tasks["task1"] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "last_heartbeat": None,
        }
        self.executor._send_heartbeat("task1")
        hb = self.executor._running_tasks["task1"]["last_heartbeat"]
        assert hb is not None
        assert isinstance(hb, datetime)

    def test_send_heartbeat_nonexistent_task_no_error(self):
        """_send_heartbeat should not raise on unknown task."""
        self.executor._send_heartbeat("nonexistent")

    def test_heartbeat_present_in_execution_status(self):
        """get_execution_status should include heartbeat fields."""
        now = datetime.now()
        self.executor._running_tasks["task1"] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": now,
            "completed_at": None,
            "last_heartbeat": now,
            "current_step": 2,
            "total_steps": 5,
        }
        status = self.executor.get_execution_status("task1")
        assert status["last_heartbeat"] is not None
        assert status["current_step"] == 2
        assert status["total_steps"] == 5


# ============================================================
# Pause / Cancel tests
# ============================================================

class TestPauseCancel:
    """Test pause and cancel with real cancellation tokens."""

    def setup_method(self):
        from app.services.collaboration.task_board import task_board
        self.executor = AgentExecutor()
        self.task_board = task_board
        self.task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="Pause Test Task",
            priority=Priority.MEDIUM
        ))
        asyncio.run(task_board.change_status(self.task.id, TaskStatus.TODO))
        asyncio.run(task_board.change_status(self.task.id, TaskStatus.IN_PROGRESS))

    def _setup_running_task(self, agent_id="agent1", status=ExecutionStatus.RUNNING):
        """Manually set up a running task in the executor."""
        self.executor._running_tasks[self.task.id] = {
            "agent_id": agent_id,
            "status": status,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }
        self.executor._agent_tasks[agent_id] = self.task.id

    @pytest.mark.asyncio
    async def test_pause_sets_cancellation_token(self):
        """pause_execution should set the cancellation token."""
        self._setup_running_task()
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()

        result = await self.executor.pause_execution(self.task.id)
        assert result is True
        assert self.executor._cancellation_tokens[self.task.id].is_set()

    @pytest.mark.asyncio
    async def test_pause_changes_status_to_paused(self):
        """pause_execution should change execution status to PAUSED."""
        self._setup_running_task()
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()

        await self.executor.pause_execution(self.task.id)
        assert self.executor._running_tasks[self.task.id]["status"] == ExecutionStatus.PAUSED

    @pytest.mark.asyncio
    async def test_pause_nonexistent_task_returns_false(self):
        """pause_execution on unknown task should return False."""
        result = await self.executor.pause_execution("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_cleans_up_task_handles(self):
        """cancel_execution should remove task handles and agent assignment."""
        self._setup_running_task()
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()
        self.executor._async_task_handles[self.task.id] = asyncio.create_task(asyncio.sleep(0))

        result = await self.executor.cancel_execution(self.task.id)
        assert result is True
        assert self.task.id not in self.executor._cancellation_tokens
        assert self.executor.get_agent_current_task("agent1") is None

    @pytest.mark.asyncio
    async def test_pause_all_pauses_running_tasks(self):
        """pause_all should pause all RUNNING tasks."""
        task2 = await self.task_board.create_task(project_id="test-project", title="Task 2", priority=Priority.MEDIUM)
        await self.task_board.change_status(task2.id, TaskStatus.TODO)
        await self.task_board.change_status(task2.id, TaskStatus.IN_PROGRESS)

        self._setup_running_task("agent1", ExecutionStatus.RUNNING)
        self.executor._running_tasks[task2.id] = {
            "agent_id": "agent2",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }
        self.executor._agent_tasks["agent2"] = task2.id
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()
        self.executor._cancellation_tokens[task2.id] = asyncio.Event()

        await self.executor.pause_all()

        assert self.executor._running_tasks[self.task.id]["status"] == ExecutionStatus.PAUSED
        assert self.executor._running_tasks[task2.id]["status"] == ExecutionStatus.PAUSED
        assert self.executor.is_global_paused() is True

    @pytest.mark.asyncio
    async def test_pause_project_only_pauses_project_tasks(self):
        """pause_project should only pause tasks belonging to the specified project."""
        # 创建另一个项目的任务
        other_task = await self.task_board.create_task(project_id="other-project", title="Other Task")
        await self.task_board.change_status(other_task.id, TaskStatus.TODO)
        await self.task_board.change_status(other_task.id, TaskStatus.IN_PROGRESS)

        self._setup_running_task("agent1", ExecutionStatus.RUNNING)
        self.executor._running_tasks[other_task.id] = {
            "agent_id": "agent2",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }
        self.executor._agent_tasks["agent2"] = other_task.id
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()
        self.executor._cancellation_tokens[other_task.id] = asyncio.Event()

        await self.executor.pause_project("test-project")

        # test-project 的任务应该被暂停
        assert self.executor._running_tasks[self.task.id]["status"] == ExecutionStatus.PAUSED
        assert self.executor.is_project_paused("test-project") is True

        # other-project 的任务不应该被暂停
        assert self.executor._running_tasks[other_task.id]["status"] == ExecutionStatus.RUNNING
        assert self.executor.is_project_paused("other-project") is False

    @pytest.mark.asyncio
    async def test_pause_all_changes_task_board_status(self):
        """pause_all should change task board status to PAUSED."""
        self._setup_running_task()
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()

        await self.executor.pause_all()

        # 验证 task_board 中的任务状态已更改
        task = self.task_board.get_task(self.task.id)
        assert task.status == TaskStatus.PAUSED

    @pytest.mark.asyncio
    async def test_cancel_execution_changes_task_board_status(self):
        """cancel_execution should change task board status to CANCELLED."""
        self._setup_running_task()
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()
        self.executor._async_task_handles[self.task.id] = asyncio.create_task(asyncio.sleep(0))

        result = await self.executor.cancel_execution(self.task.id)
        assert result is True

        # 验证 task_board 中的任务状态已更改
        task = self.task_board.get_task(self.task.id)
        assert task.status == TaskStatus.CANCELLED


# ============================================================
# Execution status tests
# ============================================================

class TestExecutionStatus:
    """Test get_execution_status with various states."""

    def setup_method(self):
        self.executor = AgentExecutor()

    def test_status_for_running_task(self):
        """Should return full status for running task."""
        now = datetime.now()
        self.executor._running_tasks["task1"] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": now,
            "completed_at": None,
            "last_heartbeat": now,
            "current_step": 1,
            "total_steps": 4,
        }
        status = self.executor.get_execution_status("task1")
        assert status["status"] == "running"
        assert status["current_step"] == 1
        assert status["total_steps"] == 4

    def test_status_for_unknown_task_returns_none(self):
        """Should return None for unknown task."""
        assert self.executor.get_execution_status("unknown") is None

    def test_status_for_completed_task(self):
        """Should return completed status."""
        now = datetime.now()
        self.executor._running_tasks["task1"] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.COMPLETED,
            "started_at": now,
            "completed_at": now,
            "last_heartbeat": now,
            "current_step": 4,
            "total_steps": 4,
        }
        status = self.executor.get_execution_status("task1")
        assert status["status"] == "completed"

    def test_get_running_tasks_filters_active(self):
        """get_running_tasks should list all tracked tasks."""
        self.executor._running_tasks["task1"] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "completed_at": None,
            "last_heartbeat": None,
            "current_step": 0,
            "total_steps": 1,
        }
        self.executor._running_tasks["task2"] = {
            "agent_id": "agent2",
            "status": ExecutionStatus.PAUSED,
            "started_at": datetime.now(),
            "completed_at": None,
            "last_heartbeat": None,
            "current_step": 2,
            "total_steps": 3,
        }
        running = self.executor.get_running_tasks()
        assert len(running) == 2


# ============================================================
# Resume execution tests
# ============================================================

class TestResumeExecution:
    """Test resume_execution logic."""

    def setup_method(self):
        from app.services.collaboration.task_board import task_board
        self.executor = AgentExecutor()
        self.task_board = task_board
        self.task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="Resume Test Task",
            priority=Priority.MEDIUM
        ))

    @pytest.mark.asyncio
    async def test_resume_from_paused_status(self):
        """resume_execution should work when status is PAUSED."""
        async def mock_fn(task):
            return {"success": True}

        await self.executor.assign_task(self.task.id, "agent1", mock_fn)
        self.executor._running_tasks[self.task.id]["status"] = ExecutionStatus.PAUSED
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()

        result = await self.executor.resume_execution(self.task.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_resume_unknown_task_returns_false(self):
        """resume_execution on unknown task should return False."""
        with patch("app.services.agent.agent_executor.task_persistence_service.load_execution", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = None
            result = await self.executor.resume_execution("nonexistent")
            assert result is False

    @pytest.mark.asyncio
    async def test_resume_already_running_returns_false(self):
        """resume_execution on already running task should return False."""
        async def mock_fn(task):
            return {"success": True}

        await self.executor.assign_task(self.task.id, "agent1", mock_fn)
        self.executor._running_tasks[self.task.id]["status"] = ExecutionStatus.RUNNING

        result = await self.executor.resume_execution(self.task.id)
        assert result is False


# ============================================================
# Fallback execution tests
# ============================================================

class TestFallbackExecution:
    """Test fallback to single execution when step planning fails."""

    def setup_method(self):
        from app.services.collaboration.task_board import task_board
        self.executor = AgentExecutor()
        self.task_board = task_board
        self.task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="Fallback Test",
            description="Test fallback execution",
            priority=Priority.MEDIUM
        ))

    @pytest.mark.asyncio
    async def test_fallback_execution_when_no_steps(self):
        """Should execute with single prompt when step planning returns empty."""
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}
        cancellation_token = asyncio.Event()

        mock_response = LLMResponse(
            content="Task completed successfully",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            model="test",
            finish_reason="stop"
        )

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            result = await self.executor._fallback_single_execution(
                self.task, agent, cancellation_token
            )
            assert result["success"] is True
            assert "Task completed" in result["result"]

    @pytest.mark.asyncio
    async def test_fallback_respects_cancellation_before_call(self):
        """Should raise CancelledError if token is set before LLM call."""
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}
        cancellation_token = asyncio.Event()
        cancellation_token.set()

        with pytest.raises(asyncio.CancelledError):
            await self.executor._fallback_single_execution(
                self.task, agent, cancellation_token
            )

    @pytest.mark.asyncio
    async def test_fallback_respects_cancellation_after_call(self):
        """Should raise CancelledError if token was set during LLM call."""
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}
        cancellation_token = asyncio.Event()

        mock_response = LLMResponse(
            content="Done",
            usage={},
            model="test",
            finish_reason="stop"
        )

        async def set_token_and_return(*args, **kwargs):
            cancellation_token.set()
            return mock_response

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = set_token_and_return

            with pytest.raises(asyncio.CancelledError):
                await self.executor._fallback_single_execution(
                    self.task, agent, cancellation_token
                )


# ============================================================
# Execute task with steps tests
# ============================================================

class TestExecuteTaskWithSteps:
    """Test the multi-step execution flow."""

    def setup_method(self):
        from app.services.collaboration.task_board import task_board
        self.executor = AgentExecutor()
        self.executor._step_timeout = 1.0
        self.task_board = task_board
        self.task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="Multi-step Test",
            description="Test multi-step execution",
            priority=Priority.MEDIUM
        ))

    @pytest.mark.asyncio
    async def test_execute_with_valid_steps(self):
        """Should execute all steps and return accumulated result."""
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}
        cancellation_token = asyncio.Event()

        self.executor._running_tasks[self.task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }

        step1 = LLMResponse(content="Step 1: DB done", usage={}, model="t", finish_reason="stop")
        step2 = LLMResponse(content="Step 2: API done", usage={}, model="t", finish_reason="stop")

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat, \
             patch("app.services.agent.agent_executor.task_persistence_service.save_execution", new_callable=AsyncMock), \
             patch("app.services.agent.agent_executor.task_persistence_service.update_heartbeat", new_callable=AsyncMock), \
             patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan, \
             patch.object(AgentExecutor, '_save_checkpoint', new_callable=AsyncMock):
            mock_chat.side_effect = [step1, step2]
            mock_plan.return_value = [
                {"name": "Create DB model", "description": "...", "expected_output": "..."},
                {"name": "Implement API", "description": "...", "expected_output": "..."},
            ]

            result = await self.executor._execute_task_with_steps(
                self.task, agent, cancellation_token
            )

        assert result["success"] is True
        assert "DB done" in result["result"]
        assert "API done" in result["result"]

    @pytest.mark.asyncio
    async def test_execute_stops_at_cancellation_boundary(self):
        """Should raise CancelledError when token is set between steps."""
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}
        cancellation_token = asyncio.Event()

        self.executor._running_tasks[self.task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }

        step_response = LLMResponse(content="Step 1 done", usage={}, model="t", finish_reason="stop")

        async def cancel_after_first(*args, **kwargs):
            cancellation_token.set()

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat, \
             patch("app.services.agent.agent_executor.task_persistence_service.save_execution", new_callable=AsyncMock), \
             patch("app.services.agent.agent_executor.task_persistence_service.update_heartbeat", new_callable=AsyncMock), \
             patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan, \
             patch.object(AgentExecutor, '_save_checkpoint', new_callable=AsyncMock) as mock_save:
            mock_chat.return_value = step_response
            mock_plan.return_value = [
                {"name": "Step 1"}, {"name": "Step 2"},
            ]
            mock_save.side_effect = cancel_after_first

            with pytest.raises(asyncio.CancelledError):
                await self.executor._execute_task_with_steps(
                    self.task, agent, cancellation_token
                )

            mock_save.assert_called()

    @pytest.mark.asyncio
    async def test_execute_falls_back_when_planning_fails(self):
        """Should fall back to single execution when step planning returns no steps."""
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}
        cancellation_token = asyncio.Event()

        self.executor._running_tasks[self.task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }

        mock_response = LLMResponse(content="Single result", usage={}, model="t", finish_reason="stop")

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat, \
             patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan:
            mock_chat.return_value = mock_response
            mock_plan.return_value = []

            result = await self.executor._execute_task_with_steps(
                self.task, agent, cancellation_token
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_with_checkpoint_resume(self):
        """Should start from checkpoint step when start_from_step > 0."""
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}
        cancellation_token = asyncio.Event()

        self.executor._running_tasks[self.task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }

        step3 = LLMResponse(content="Step 3 done", usage={}, model="t", finish_reason="stop")

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat, \
             patch("app.services.agent.agent_executor.task_persistence_service.save_execution", new_callable=AsyncMock), \
             patch("app.services.agent.agent_executor.task_persistence_service.update_heartbeat", new_callable=AsyncMock), \
             patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan, \
             patch.object(AgentExecutor, '_save_checkpoint', new_callable=AsyncMock):
            mock_chat.return_value = step3
            mock_plan.return_value = [{"name": "Step 1"}, {"name": "Step 2"}, {"name": "Step 3"}]

            result = await self.executor._execute_task_with_steps(
                self.task, agent, cancellation_token, start_from_step=2
            )

        assert result["success"] is True
        mock_chat.assert_called_once()


# ============================================================
# execute_task_with_agent integration tests
# ============================================================

class TestExecuteTaskWithAgent:
    """Test the main execute_task_with_agent flow."""

    def setup_method(self):
        from app.services.collaboration.task_board import task_board
        self.executor = AgentExecutor()
        self.task_board = task_board
        self.task = asyncio.run(task_board.create_task(
            project_id="test-project",
            title="Integration Test Task",
            description="Full integration test",
            priority=Priority.MEDIUM
        ))

    @pytest.mark.asyncio
    async def test_execute_with_steps_success(self):
        """Should successfully execute task with planned steps."""
        await self.task_board.change_status(self.task.id, TaskStatus.TODO)
        await self.task_board.change_status(self.task.id, TaskStatus.IN_PROGRESS)

        with patch("app.services.agent.agent_executor.agent_service") as mock_agent_svc:
            mock_agent_svc.get_agent.return_value = {
                "id": "agent1",
                "name": "Test Agent",
                "system_prompt": "You are helpful.",
            }
            mock_agent_svc.get_agent_project.return_value = None

            self.executor._running_tasks = {}

            step1 = LLMResponse(content="Step 1 done", usage={}, model="t", finish_reason="stop")
            step2 = LLMResponse(content="Step 2 done", usage={}, model="t", finish_reason="stop")

            with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat, \
                 patch("app.services.agent.agent_executor.task_persistence_service.save_execution", new_callable=AsyncMock), \
                 patch("app.services.agent.agent_executor.task_persistence_service.update_heartbeat", new_callable=AsyncMock), \
                 patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan, \
                 patch.object(AgentExecutor, '_save_checkpoint', new_callable=AsyncMock), \
                 patch("app.services.execution.checkpoint_manager.checkpoint_manager.load_checkpoint", new_callable=AsyncMock) as mock_load:
                mock_chat.side_effect = [step1, step2]
                mock_plan.return_value = [
                    {"name": "Step 1", "description": "First step", "expected_output": "Output1"},
                    {"name": "Step 2", "description": "Second step", "expected_output": "Output2"},
                ]
                mock_load.return_value = None

                result = await self.executor.execute_task_with_agent(
                    self.task.id, "agent1"
                )

        assert result["success"] is True
        assert "Step 1 done" in result["result"]
        assert "Step 2 done" in result["result"]

    @pytest.mark.asyncio
    async def test_execute_with_cancellation(self):
        """Should return paused=True when cancelled."""
        await self.task_board.change_status(self.task.id, TaskStatus.TODO)
        await self.task_board.change_status(self.task.id, TaskStatus.IN_PROGRESS)

        with patch("app.services.agent.agent_executor.agent_service") as mock_agent_svc:
            mock_agent_svc.get_agent.return_value = {
                "id": "agent1",
                "name": "Test Agent",
                "system_prompt": "You are helpful.",
            }
            mock_agent_svc.get_agent_project.return_value = None

            self.executor._running_tasks = {}

            async def cancel(*args, **kwargs):
                self.executor._cancellation_tokens.get(self.task.id, asyncio.Event()).set()
                raise asyncio.CancelledError("Task cancelled")

            with patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan, \
                 patch("app.services.execution.checkpoint_manager.checkpoint_manager.load_checkpoint", new_callable=AsyncMock) as mock_load:
                mock_plan.side_effect = cancel
                mock_load.return_value = None

                result = await self.executor.execute_task_with_agent(
                    self.task.id, "agent1"
                )

        assert result["success"] is False
        assert result.get("paused") is True

    @pytest.mark.asyncio
    async def test_execute_task_not_found(self):
        """Should return error when task doesn't exist."""
        result = await self.executor.execute_task_with_agent("nonexistent", "agent1")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_agent_not_found(self):
        """Should return error when agent doesn't exist."""
        with patch("app.services.agent.agent_executor.agent_service") as mock_agent_svc:
            mock_agent_svc.get_agent.return_value = None

            result = await self.executor.execute_task_with_agent(self.task.id, "agent1")

        assert result["success"] is False
        assert "not found" in result["error"].lower()
