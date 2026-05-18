"""
Integration tests for execution recovery system.

Tests real service interactions with in-memory SQLite and MockLLM.
Covers: full step-based execution, pause/resume with checkpoint,
stuck detection, checkpoint persistence, fallback execution.
"""
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.task import TaskStatus, Priority
from app.services.agent.agent_executor import AgentExecutor, ExecutionStatus
from app.services.collaboration.task_board import task_board, TaskBoard
from app.services.collaboration.message_bus import message_bus
from app.services.execution.task_persistence_service import TaskPersistenceService
from app.services.execution.checkpoint_manager import CheckpointManager
from app.services.execution.stuck_detector import StuckDetector
from app.core.llm import LLMResponse


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def setup_services():
    """Reset in-memory services before each test."""
    task_board.clear_all()
    message_bus.clear_history()
    yield


class TestIntegrationFullExecution:
    """Test the full step-based execution flow with real services."""

    def setup_method(self):
        self.executor = AgentExecutor()
        self.executor._step_timeout = 5.0
        self.persistence = TaskPersistenceService()
        self.checkpoints = CheckpointManager()
        self.detector = StuckDetector(heartbeat_threshold_seconds=0.5, check_interval_seconds=0.2)

    def _create_task_in_progress(self):
        """Helper: create a task and transition to IN_PROGRESS."""
        task = task_board.create_task(
            title="Integration Test Task",
            description="Test full execution flow",
            priority=Priority.MEDIUM
        )
        task_board.change_status(task.id, TaskStatus.TODO)
        task_board.change_status(task.id, TaskStatus.IN_PROGRESS)
        return task

    @pytest.mark.asyncio
    async def test_full_step_execution_with_mock_llm(self):
        """Execute a task with planned steps and get accumulated result."""
        task = self._create_task_in_progress()
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}

        step1 = LLMResponse(content="Step 1 result", usage={}, model="test", finish_reason="stop")
        step2 = LLMResponse(content="Step 2 result", usage={}, model="test", finish_reason="stop")

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat, \
             patch("app.services.agent.agent_executor.task_persistence_service.save_execution", new_callable=AsyncMock), \
             patch("app.services.agent.agent_executor.task_persistence_service.update_heartbeat", new_callable=AsyncMock), \
             patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan, \
             patch.object(AgentExecutor, '_save_checkpoint', new_callable=AsyncMock):
            mock_chat.side_effect = [step1, step2]
            mock_plan.return_value = [
                {"name": "Analyze"}, {"name": "Implement"},
            ]

            result = await self.executor._execute_task_with_steps(
                task, agent, asyncio.Event()
            )

        assert result["success"] is True
        assert "Step 1 result" in result["result"]
        assert "Step 2 result" in result["result"]

    @pytest.mark.asyncio
    async def test_execution_stops_at_cancellation(self):
        """Task execution should stop at cancellation boundary between steps."""
        task = self._create_task_in_progress()
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}
        cancellation_token = asyncio.Event()

        self.executor._running_tasks[task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }

        step_resp = LLMResponse(content="Step 1 done", usage={}, model="test", finish_reason="stop")

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat, \
             patch("app.services.agent.agent_executor.task_persistence_service.save_execution", new_callable=AsyncMock), \
             patch("app.services.agent.agent_executor.task_persistence_service.update_heartbeat", new_callable=AsyncMock), \
             patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan, \
             patch.object(AgentExecutor, '_save_checkpoint', new_callable=AsyncMock) as mock_save:
            mock_chat.return_value = step_resp
            mock_plan.return_value = [{"name": "Step 1"}, {"name": "Step 2"}, {"name": "Step 3"}]

            async def set_cancel(*args, **kwargs):
                cancellation_token.set()

            mock_save.side_effect = set_cancel

            with pytest.raises(asyncio.CancelledError):
                await self.executor._execute_task_with_steps(
                    task, agent, cancellation_token
                )

    @pytest.mark.asyncio
    async def test_fallback_when_planning_fails(self):
        """Should fall back to single-call execution when step planning returns empty."""
        task = self._create_task_in_progress()
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}

        single_resp = LLMResponse(content="Direct execution result", usage={}, model="test", finish_reason="stop")

        with patch("app.services.agent.agent_executor.llm_service.chat", new_callable=AsyncMock) as mock_chat, \
             patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan:
            mock_chat.return_value = single_resp
            mock_plan.return_value = []

            result = await self.executor._execute_task_with_steps(
                task, agent, asyncio.Event()
            )

        assert result["success"] is True
        assert "Direct execution result" in result["result"]

    @pytest.mark.asyncio
    async def test_cancellation_before_execution(self):
        """Should raise CancelledError when token is set before execution starts."""
        task = self._create_task_in_progress()
        agent = {"id": "agent1", "name": "Dev", "system_prompt": "You are helpful."}

        cancellation_token = asyncio.Event()
        cancellation_token.set()

        self.executor._running_tasks[task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }

        with patch.object(AgentExecutor, '_plan_task_steps', new_callable=AsyncMock) as mock_plan, \
             patch("app.services.agent.agent_executor.task_persistence_service.save_execution", new_callable=AsyncMock):
            mock_plan.return_value = [{"name": "Step 1"}]

            with pytest.raises(asyncio.CancelledError):
                await self.executor._execute_task_with_steps(
                    task, agent, cancellation_token
                )


class TestCheckpointPersistence:
    """Test checkpoint save/load with real in-memory SQLite."""

    @pytest_asyncio.fixture
    async def db_session(self):
        test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        persistence = TaskPersistenceService()
        persistence.initialize(session_factory)

        yield persistence

        await test_engine.dispose()

    @pytest.mark.asyncio
    async def test_save_and_load_execution(self, db_session):
        """Should persist execution state and load it back."""
        await db_session.save_execution(
            task_id="task-1",
            agent_id="agent-1",
            status="running",
            current_step_index=2,
            total_steps=4,
        )

        loaded = await db_session.load_execution("task-1")
        assert loaded is not None
        assert loaded["task_id"] == "task-1"
        assert loaded["status"] == "running"
        assert loaded["current_step_index"] == 2
        assert loaded["total_steps"] == 4

    @pytest.mark.asyncio
    async def test_save_and_update_execution(self, db_session):
        """Should update existing execution record."""
        await db_session.save_execution(task_id="task-1", agent_id="agent-1", status="running", current_step_index=0)
        await db_session.save_execution(task_id="task-1", agent_id="agent-1", status="running", current_step_index=3, total_steps=5)

        loaded = await db_session.load_execution("task-1")
        assert loaded["current_step_index"] == 3
        assert loaded["total_steps"] == 5

    @pytest.mark.asyncio
    async def test_load_nonexistent_execution(self, db_session):
        """Should return None for unknown task."""
        loaded = await db_session.load_execution("nonexistent")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(self, db_session):
        """Should persist a checkpoint and load the latest one."""
        cid = await db_session.save_checkpoint(
            task_id="task-1",
            step_index=0,
            step_name="Analyze requirements",
            context={"messages_snapshot": [{"role": "user", "content": "hello"}]},
            partial_result="Analysis complete",
        )
        assert cid is not None

        checkpoint = await db_session.load_latest_checkpoint("task-1")
        assert checkpoint is not None
        assert checkpoint["step_index"] == 0
        assert checkpoint["step_name"] == "Analyze requirements"
        assert checkpoint["partial_result"] == "Analysis complete"

    @pytest.mark.asyncio
    async def test_latest_checkpoint_is_most_recent(self, db_session):
        """Should return the checkpoint with the highest step_index."""
        await db_session.save_checkpoint(task_id="task-1", step_index=0, step_name="Step 1", partial_result="R1")
        await db_session.save_checkpoint(task_id="task-1", step_index=1, step_name="Step 2", partial_result="R2")
        await db_session.save_checkpoint(task_id="task-1", step_index=2, step_name="Step 3", partial_result="R3")

        latest = await db_session.load_latest_checkpoint("task-1")
        assert latest["step_index"] == 2
        assert latest["step_name"] == "Step 3"

    @pytest.mark.asyncio
    async def test_list_all_checkpoints(self, db_session):
        """Should list all checkpoints for a task in step order."""
        await db_session.save_checkpoint(task_id="task-1", step_index=0, step_name="S1")
        await db_session.save_checkpoint(task_id="task-1", step_index=1, step_name="S2")

        checkpoints = await db_session.list_checkpoints("task-1")
        assert len(checkpoints) == 2
        assert checkpoints[0]["step_index"] == 0
        assert checkpoints[1]["step_index"] == 1

    @pytest.mark.asyncio
    async def test_heartbeat_update(self, db_session):
        """Should update heartbeat timestamp."""
        await db_session.save_execution(task_id="task-1", agent_id="agent-1", status="running")

        before = datetime.now()
        await db_session.update_heartbeat("task-1", step_index=1, total_steps=3)
        after = datetime.now()

        loaded = await db_session.load_execution("task-1")
        assert loaded["last_heartbeat"] is not None
        assert isinstance(loaded["last_heartbeat"], datetime)

    @pytest.mark.asyncio
    async def test_delete_execution(self, db_session):
        """Should delete execution record."""
        await db_session.save_execution(task_id="task-1", agent_id="agent-1", status="running")
        await db_session.delete_execution("task-1")

        loaded = await db_session.load_execution("task-1")
        assert loaded is None


class TestCheckpointManager:
    """Test CheckpointManager functionality."""

    def setup_method(self):
        self.manager = CheckpointManager()

    @pytest.mark.asyncio
    async def test_build_resume_context(self):
        """Should build resume prompt with previous step info."""
        checkpoint = {
            "step_index": 2,
            "step_name": "Implement API",
            "partial_result": "Already done: DB model, API routes",
            "context": {"messages_snapshot": [{"role": "user", "content": "test"}]},
        }

        resume_prompt, messages = self.manager.build_resume_context(checkpoint)

        assert "3 个步骤" in resume_prompt
        assert "Implement API" in resume_prompt
        assert "DB model" in resume_prompt
        assert "不要重复已完成的工作" in resume_prompt
        assert len(messages) == 1


class TestStuckDetector:
    """Test stuck detection logic."""

    def setup_method(self):
        self.detector = StuckDetector(heartbeat_threshold_seconds=10.0, check_interval_seconds=0.1)

    @pytest.mark.asyncio
    async def test_detect_stuck_by_no_heartbeat(self):
        """Should detect tasks that haven't sent a heartbeat."""
        with patch("app.services.agent.agent_executor.agent_executor") as mock_executor:
            now = datetime.now()
            mock_executor.get_running_tasks.return_value = [
                {
                    "task_id": "task-1",
                    "agent_id": "agent-1",
                    "status": "running",
                    "last_heartbeat": (now - timedelta(seconds=30)).isoformat(),
                    "current_step": 1,
                    "total_steps": 4,
                }
            ]

            stuck = await self.detector.check_stuck_tasks()
            assert len(stuck) == 1
            assert stuck[0]["task_id"] == "task-1"
            assert stuck[0]["reason"] == "heartbeat_timeout"

    @pytest.mark.asyncio
    async def test_no_stuck_when_heartbeat_recent(self):
        """Should NOT mark tasks with recent heartbeat as stuck."""
        with patch("app.services.agent.agent_executor.agent_executor") as mock_executor:
            now = datetime.now()
            mock_executor.get_running_tasks.return_value = [
                {
                    "task_id": "task-1",
                    "agent_id": "agent-1",
                    "status": "running",
                    "last_heartbeat": (now - timedelta(seconds=5)).isoformat(),
                    "current_step": 1,
                    "total_steps": 4,
                }
            ]

            stuck = await self.detector.check_stuck_tasks()
            assert len(stuck) == 0

    @pytest.mark.asyncio
    async def test_detect_stuck_no_heartbeat_ever(self):
        """Should detect tasks that never sent a heartbeat but started long ago."""
        with patch("app.services.agent.agent_executor.agent_executor") as mock_executor:
            now = datetime.now()
            mock_executor.get_running_tasks.return_value = [
                {
                    "task_id": "task-2",
                    "agent_id": "agent-2",
                    "status": "running",
                    "last_heartbeat": None,
                    "started_at": (now - timedelta(seconds=30)).isoformat(),
                    "current_step": 0,
                    "total_steps": 1,
                }
            ]

            stuck = await self.detector.check_stuck_tasks()
            assert len(stuck) == 1
            assert stuck[0]["reason"] == "no_heartbeat_ever"

    @pytest.mark.asyncio
    async def test_ignore_non_running_tasks(self):
        """Should only check RUNNING tasks for stuck detection."""
        with patch("app.services.agent.agent_executor.agent_executor") as mock_executor:
            mock_executor.get_running_tasks.return_value = [
                {"task_id": "task-1", "agent_id": "a1", "status": "paused", "last_heartbeat": None},
                {"task_id": "task-2", "agent_id": "a2", "status": "completed", "last_heartbeat": None},
                {"task_id": "task-3", "agent_id": "a3", "status": "cancelled", "last_heartbeat": None},
            ]

            stuck = await self.detector.check_stuck_tasks()
            assert len(stuck) == 0


class TestPauseResumeFlow:
    """Test the pause and resume flow end to end."""

    def setup_method(self):
        from app.services.collaboration.task_board import task_board
        self.executor = AgentExecutor()
        self.task = task_board.create_task(title="Pause Resume Test", priority=Priority.MEDIUM)
        task_board.change_status(self.task.id, TaskStatus.TODO)
        task_board.change_status(self.task.id, TaskStatus.IN_PROGRESS)

    @pytest.mark.asyncio
    async def test_pause_sets_token_and_changes_status(self):
        """Pausing should set the cancellation token and change execution status."""
        self.executor._running_tasks[self.task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 1,
            "total_steps": 4,
        }
        self.executor._agent_tasks["agent1"] = self.task.id
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()

        result = await self.executor.pause_execution(self.task.id)
        assert result is True
        assert self.executor._cancellation_tokens[self.task.id].is_set()
        assert self.executor._running_tasks[self.task.id]["status"] == ExecutionStatus.PAUSED

    @pytest.mark.asyncio
    async def test_resume_from_paused(self):
        """Resuming should transition back to RUNNING."""
        self.executor._running_tasks[self.task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.PAUSED,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 2,
            "total_steps": 4,
        }
        self.executor._agent_tasks["agent1"] = self.task.id
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()

        with patch("app.services.agent.agent_executor.task_persistence_service.load_execution", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = None
            result = await self.executor.resume_execution(self.task.id)
            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_from_running(self):
        """Cancelling should remove task handles and set CANCELLED."""
        self.executor._running_tasks[self.task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }
        self.executor._agent_tasks["agent1"] = self.task.id
        self.executor._cancellation_tokens[self.task.id] = asyncio.Event()

        result = await self.executor.cancel_execution(self.task.id)
        assert result is True
        assert self.executor.get_agent_current_task("agent1") is None

    @pytest.mark.asyncio
    async def test_pause_nonexistent_returns_false(self):
        """Pausing a non-existent task should return False."""
        result = await self.executor.pause_execution("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_nonexistent_returns_false(self):
        """Resuming a non-existent task should return False."""
        with patch("app.services.agent.agent_executor.task_persistence_service.load_execution", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = None
            result = await self.executor.resume_execution("nonexistent")
            assert result is False

    @pytest.mark.asyncio
    async def test_resume_already_running_returns_false(self):
        """Resuming an already running task should return False."""
        self.executor._running_tasks[self.task.id] = {
            "agent_id": "agent1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "current_step": 0,
            "total_steps": 1,
        }

        result = await self.executor.resume_execution(self.task.id)
        assert result is False


class TestExecutionStatusReporting:
    """Test execution status and heartbeat reporting."""

    def setup_method(self):
        self.executor = AgentExecutor()

    def test_status_includes_all_fields(self):
        """Execution status should include task_id, agent_id, status, heartbeat, steps."""
        now = datetime.now()
        self.executor._running_tasks["task-1"] = {
            "agent_id": "agent-1",
            "status": ExecutionStatus.RUNNING,
            "started_at": now,
            "completed_at": None,
            "last_heartbeat": now,
            "current_step": 3,
            "total_steps": 8,
        }

        status = self.executor.get_execution_status("task-1")
        assert status["task_id"] == "task-1"
        assert status["agent_id"] == "agent-1"
        assert status["status"] == "running"
        assert status["last_heartbeat"] is not None
        assert status["current_step"] == 3
        assert status["total_steps"] == 8

    def test_status_unknown_returns_none(self):
        """get_execution_status should return None for unknown task."""
        assert self.executor.get_execution_status("unknown") is None

    def test_get_running_tasks_returns_all(self):
        """get_running_tasks should list all tracked tasks regardless of status."""
        self.executor._running_tasks["task-1"] = {
            "agent_id": "a1",
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.now(),
            "completed_at": None,
            "last_heartbeat": None,
            "current_step": 0, "total_steps": 1,
        }
        self.executor._running_tasks["task-2"] = {
            "agent_id": "a2",
            "status": ExecutionStatus.PAUSED,
            "started_at": datetime.now(),
            "completed_at": None,
            "last_heartbeat": None,
            "current_step": 2, "total_steps": 5,
        }

        running = self.executor.get_running_tasks()
        assert len(running) == 2

    def test_heartbeat_updates_timestamp(self):
        """Heartbeat should set last_heartbeat to current time."""
        self.executor._running_tasks["task-1"] = {
            "agent_id": "a1",
            "status": ExecutionStatus.RUNNING,
            "last_heartbeat": None,
            "current_step": 0,
            "total_steps": 1,
        }

        self.executor._send_heartbeat("task-1")
        assert self.executor._running_tasks["task-1"]["last_heartbeat"] is not None

    def test_heartbeat_nonexistent_no_error(self):
        """Heartbeat on unknown task should not raise."""
        self.executor._send_heartbeat("nonexistent")


class TestAgentAssignment:
    """Test agent to task assignment validation."""

    def setup_method(self):
        self.executor = AgentExecutor()

    @pytest.mark.asyncio
    async def test_assign_task_backlog_ok(self):
        """Should allow assigning a task in BACKLOG status."""
        task = task_board.create_task(title="Backlog Task")
        async def mock_fn(t):
            return {"success": True}

        result = await self.executor.assign_task(task.id, "agent1", mock_fn)
        assert result is True

    @pytest.mark.asyncio
    async def test_assign_task_todo_ok(self):
        """Should allow assigning a task in TODO status."""
        task = task_board.create_task(title="Todo Task")
        task_board.change_status(task.id, TaskStatus.TODO)
        async def mock_fn(t):
            return {"success": True}

        result = await self.executor.assign_task(task.id, "agent1", mock_fn)
        assert result is True

    @pytest.mark.asyncio
    async def test_assign_task_in_progress_fails(self):
        """Should NOT allow assigning a task already IN_PROGRESS."""
        task = task_board.create_task(title="In Progress Task")
        task_board.change_status(task.id, TaskStatus.TODO)
        task_board.change_status(task.id, TaskStatus.IN_PROGRESS)
        async def mock_fn(t):
            return {"success": True}

        result = await self.executor.assign_task(task.id, "agent1", mock_fn)
        assert result is False

    @pytest.mark.asyncio
    async def test_assign_task_nonexistent_fails(self):
        """Should return False for non-existent task."""
        async def mock_fn(t):
            return {"success": True}

        result = await self.executor.assign_task("nonexistent", "agent1", mock_fn)
        assert result is False
