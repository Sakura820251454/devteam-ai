"""StuckDetector 单元测试 — 卡死检测。

覆盖 start/stop monitoring / check_stuck_tasks / _handle_stuck_task / is_running。

不使用 datetime patch，用真实时间偏移控制阈值判断。
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.execution.stuck_detector import StuckDetector


class TestStartStop:
    """启动和停止监控。"""

    @pytest.mark.asyncio
    async def test_start_monitoring(self):
        detector = StuckDetector(heartbeat_threshold_seconds=60, check_interval_seconds=999)
        await detector.start_monitoring()
        assert detector.is_running is True
        assert detector._monitor_task is not None
        await detector.stop_monitoring()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        detector = StuckDetector(check_interval_seconds=999)
        await detector.start_monitoring()
        task1 = detector._monitor_task
        await detector.start_monitoring()
        task2 = detector._monitor_task
        assert task1 is task2
        await detector.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self):
        detector = StuckDetector(check_interval_seconds=999)
        await detector.start_monitoring()
        await detector.stop_monitoring()
        assert detector.is_running is False
        assert detector._monitor_task is None

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        detector = StuckDetector()
        await detector.stop_monitoring()
        assert detector.is_running is False


class TestCheckStuckTasks:
    """check_stuck_tasks 检测逻辑。"""

    def _mock_exec(self, tasks):
        mock_exec = MagicMock()
        mock_exec.get_running_tasks.return_value = tasks
        return mock_exec

    @pytest.mark.asyncio
    async def test_no_heartbeat_ever_exceeds_threshold(self):
        """从未有心跳且启动时间很早 → 卡死。"""
        detector = StuckDetector(heartbeat_threshold_seconds=10)
        long_ago = datetime.now() - timedelta(hours=2)

        mock_exec = self._mock_exec([{
            "task_id": "task-1",
            "agent_id": "agent-a",
            "status": "running",
            "started_at": long_ago.isoformat(),
            "last_heartbeat": None,
            "current_step": 1,
            "total_steps": 5,
        }])

        with patch("app.services.agent.agent_executor.agent_executor", mock_exec):
            stuck = await detector.check_stuck_tasks()
            assert len(stuck) == 1
            assert stuck[0]["task_id"] == "task-1"
            assert stuck[0]["reason"] == "no_heartbeat_ever"

    @pytest.mark.asyncio
    async def test_heartbeat_timeout(self):
        """心跳超时 → 卡死。"""
        detector = StuckDetector(heartbeat_threshold_seconds=10)
        long_ago = datetime.now() - timedelta(hours=2)

        mock_exec = self._mock_exec([{
            "task_id": "task-2",
            "agent_id": "agent-b",
            "status": "running",
            "started_at": long_ago.isoformat(),
            "last_heartbeat": long_ago + timedelta(minutes=30),  # 1.5h前心跳，已超阈值
            "current_step": 3,
            "total_steps": 5,
        }])

        with patch("app.services.agent.agent_executor.agent_executor", mock_exec):
            stuck = await detector.check_stuck_tasks()
            assert len(stuck) == 1
            assert stuck[0]["reason"] == "heartbeat_timeout"

    @pytest.mark.asyncio
    async def test_within_threshold_not_stuck(self):
        """心跳在阈值内 → 不卡死。"""
        detector = StuckDetector(heartbeat_threshold_seconds=99999)  # 大阈值
        now = datetime.now()

        mock_exec = self._mock_exec([{
            "task_id": "task-3",
            "agent_id": "agent-c",
            "status": "running",
            "started_at": (now - timedelta(hours=1)).isoformat(),
            "last_heartbeat": now - timedelta(seconds=5),  # 5s前，远小于阈值
            "current_step": 2,
            "total_steps": 5,
        }])

        with patch("app.services.agent.agent_executor.agent_executor", mock_exec):
            stuck = await detector.check_stuck_tasks()
            assert len(stuck) == 0

    @pytest.mark.asyncio
    async def test_skips_non_running_tasks(self):
        """非 running 状态的任务跳过。"""
        detector = StuckDetector(heartbeat_threshold_seconds=1)
        long_ago = datetime.now() - timedelta(hours=10)

        mock_exec = self._mock_exec([{
            "task_id": "task-4",
            "agent_id": "agent-d",
            "status": "paused",
            "started_at": long_ago.isoformat(),
            "last_heartbeat": None,
        }])

        with patch("app.services.agent.agent_executor.agent_executor", mock_exec):
            stuck = await detector.check_stuck_tasks()
            assert len(stuck) == 0

    @pytest.mark.asyncio
    async def test_no_running_tasks(self):
        """没有运行中任务时返回空列表。"""
        detector = StuckDetector()
        mock_exec = self._mock_exec([])

        with patch("app.services.agent.agent_executor.agent_executor", mock_exec):
            stuck = await detector.check_stuck_tasks()
            assert stuck == []

    @pytest.mark.asyncio
    async def test_task_without_started_at(self):
        """没有 started_at 时跳过。"""
        detector = StuckDetector(heartbeat_threshold_seconds=1)

        mock_exec = self._mock_exec([{
            "task_id": "task-5",
            "agent_id": "agent-e",
            "status": "running",
            "started_at": None,
            "last_heartbeat": None,
        }])

        with patch("app.services.agent.agent_executor.agent_executor", mock_exec):
            stuck = await detector.check_stuck_tasks()
            assert len(stuck) == 0

    @pytest.mark.asyncio
    async def test_heartbeat_string_conversion(self):
        """last_heartbeat 为 ISO 字符串时正确解析。"""
        detector = StuckDetector(heartbeat_threshold_seconds=10)
        long_ago = datetime.now() - timedelta(hours=2)

        mock_exec = self._mock_exec([{
            "task_id": "task-6",
            "agent_id": "agent-f",
            "status": "running",
            "started_at": long_ago.isoformat(),
            "last_heartbeat": long_ago.isoformat(),  # 字符串格式
            "current_step": 1,
            "total_steps": 3,
        }])

        with patch("app.services.agent.agent_executor.agent_executor", mock_exec):
            stuck = await detector.check_stuck_tasks()
            assert len(stuck) == 1

    @pytest.mark.asyncio
    async def test_no_heartbeat_within_threshold(self):
        """从未有心跳但启动时间很近 → 不卡死。"""
        detector = StuckDetector(heartbeat_threshold_seconds=99999)  # 大阈值
        now = datetime.now()

        mock_exec = self._mock_exec([{
            "task_id": "task-7",
            "agent_id": "agent-g",
            "status": "running",
            "started_at": (now - timedelta(seconds=30)).isoformat(),
            "last_heartbeat": None,
            "current_step": 1,
            "total_steps": 5,
        }])

        with patch("app.services.agent.agent_executor.agent_executor", mock_exec):
            stuck = await detector.check_stuck_tasks()
            assert len(stuck) == 0


class TestHandleStuckTask:
    """_handle_stuck_task 处理卡死任务。"""

    @pytest.mark.asyncio
    async def test_handle_stuck_task_adds_comment_and_broadcasts(self):
        detector = StuckDetector()
        stuck_info = {
            "task_id": "task-x",
            "agent_id": "agent-x",
            "reason": "heartbeat_timeout",
            "elapsed_seconds": 180,
            "current_step": 2,
            "total_steps": 5,
        }

        with patch(
            "app.services.collaboration.task_board.task_board"
        ) as mock_board, patch(
            "app.services.collaboration.message_bus.message_bus"
        ) as mock_bus:
            mock_bus.broadcast = AsyncMock()

            await detector._handle_stuck_task(stuck_info)

            mock_board.add_comment.assert_called_once()
            call_args = mock_board.add_comment.call_args
            assert call_args[0][0] == "task-x"
            assert "卡死检测" in call_args[0][1]

            mock_bus.broadcast.assert_called_once()
            broadcast_msg = mock_bus.broadcast.call_args[0][0]
            assert "task-x" in broadcast_msg.content
            assert "agent-x" in broadcast_msg.content
