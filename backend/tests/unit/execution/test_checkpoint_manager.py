"""CheckpointManager 单元测试 — 检查点保存/恢复/上下文构建。"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.execution.checkpoint_manager import CheckpointManager


class TestBuildResumeContext:
    """build_resume_context 从检查点构建恢复上下文。"""

    def test_build_resume_context(self):
        mgr = CheckpointManager()
        checkpoint = {
            "partial_result": "已完成步骤1和步骤2的分析",
            "step_name": "数据分析",
            "step_index": 2,
            "context": {
                "messages_snapshot": [{"role": "assistant", "content": "分析中..."}],
            },
        }

        with patch("app.services.execution.checkpoint_manager.registry") as mock_reg:
            mock_reg.render.return_value = "[resume prompt]"
            resume_prompt, messages = mgr.build_resume_context(checkpoint)

            assert messages == [{"role": "assistant", "content": "分析中..."}]
            assert resume_prompt == "[resume prompt]"
            # prompt 渲染参数应为 step_index+1
            mock_reg.render.assert_called_once()
            args, _kwargs = mock_reg.render.call_args
            render_vars = args[1]  # 第二个位置参数
            assert render_vars["step_index"] == 3  # step_index + 1
            assert render_vars["step_name"] == "数据分析"

    def test_build_resume_context_empty(self):
        mgr = CheckpointManager()
        checkpoint = {
            "partial_result": "",
            "step_name": "",
            "step_index": 0,
            "context": {},
        }

        with patch("app.services.execution.checkpoint_manager.registry") as mock_reg:
            mock_reg.render.return_value = "[resume]"
            resume_prompt, messages = mgr.build_resume_context(checkpoint)

            assert messages == []
            assert resume_prompt == "[resume]"

    def test_build_resume_context_missing_messages(self):
        """context 中没有 messages_snapshot 时返回空列表。"""
        mgr = CheckpointManager()
        checkpoint = {
            "partial_result": "结果",
            "step_name": "step",
            "step_index": 1,
            "context": {"other": "data"},
        }

        with patch("app.services.execution.checkpoint_manager.registry") as mock_reg:
            mock_reg.render.return_value = "[prompt]"
            _, messages = mgr.build_resume_context(checkpoint)

            assert messages == []


class TestSaveCheckpoint:
    """save_checkpoint 保存检查点。"""

    @pytest.mark.asyncio
    async def test_save_checkpoint(self):
        mgr = CheckpointManager()
        with patch(
            "app.services.execution.checkpoint_manager.task_persistence_service"
        ) as mock_svc:
            mock_svc.save_checkpoint = AsyncMock(return_value="ckpt-001")

            ckpt_id = await mgr.save_checkpoint(
                task_id="task-1",
                step_index=3,
                step_name="test_step",
                messages_snapshot=[{"role": "user", "content": "hello"}],
                partial_result="已完成",
                agent_state={"key": "val"},
            )

            assert ckpt_id == "ckpt-001"
            mock_svc.save_checkpoint.assert_called_once()
            call_kwargs = mock_svc.save_checkpoint.call_args.kwargs
            assert call_kwargs["task_id"] == "task-1"
            assert call_kwargs["step_index"] == 3
            # messages_snapshot 应只保留最近 10 条
            assert len(call_kwargs["context"]["messages_snapshot"]) == 1


class TestLoadCheckpoint:
    """load_checkpoint 加载检查点。"""

    @pytest.mark.asyncio
    async def test_load_checkpoint(self):
        mgr = CheckpointManager()
        expected = {"task_id": "task-1", "step_index": 2}
        with patch(
            "app.services.execution.checkpoint_manager.task_persistence_service"
        ) as mock_svc:
            mock_svc.load_latest_checkpoint = AsyncMock(return_value=expected)
            result = await mgr.load_checkpoint("task-1")
            assert result == expected

    @pytest.mark.asyncio
    async def test_load_checkpoint_none(self):
        mgr = CheckpointManager()
        with patch(
            "app.services.execution.checkpoint_manager.task_persistence_service"
        ) as mock_svc:
            mock_svc.load_latest_checkpoint = AsyncMock(return_value=None)
            result = await mgr.load_checkpoint("task-1")
            assert result is None


class TestListCheckpoints:
    """list_checkpoints 列出检查点。"""

    @pytest.mark.asyncio
    async def test_list_checkpoints(self):
        mgr = CheckpointManager()
        expected = [{"id": "1"}, {"id": "2"}]
        with patch(
            "app.services.execution.checkpoint_manager.task_persistence_service"
        ) as mock_svc:
            mock_svc.list_checkpoints = AsyncMock(return_value=expected)
            result = await mgr.list_checkpoints("task-1")
            assert len(result) == 2
