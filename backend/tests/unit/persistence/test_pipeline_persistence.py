"""Pipeline 持久化层单元测试。

测试 _model_from_pipeline / _pipeline_from_model 转换逻辑，
以及 paused 列的兼容性修复。
"""

import pytest
from datetime import datetime

from app.services.collaboration.pipeline_orchestrator import Pipeline, PipelineStatus
from app.services.persistence.pipeline_persistence import (
    _model_from_pipeline,
    _pipeline_from_model,
)
from app.models.core_db import PipelineModel
from tests.factories import PipelineFactory


# ========== 模型转换 ==========


class TestModelConversion:
    """Pipeline ↔ PipelineModel 转换测试。"""

    def test_pipeline_to_model_basic(self):
        """Pipeline 转换为 PipelineModel 时字段应对应正确。"""
        p = PipelineFactory.create(
            id="p-001",
            project_id="proj-001",
            name="测试流水线",
            status=PipelineStatus.RUNNING,
            agents=["agent-1", "agent-2"],
            stages=[{"key": "collect", "label": "收集"}],
            progress=0.5,
        )
        m = _model_from_pipeline(p)

        assert m.id == "p-001"
        assert m.project_id == "proj-001"
        assert m.name == "测试流水线"
        assert m.status == "running"
        assert m.agents == ["agent-1", "agent-2"]
        assert m.stages == [{"key": "collect", "label": "收集"}]
        assert m.progress == 0.5

    def test_pipeline_to_model_paused_flag(self):
        """PAUSED 状态的 Pipeline 转换后 paused 列为 True。"""
        p = PipelineFactory.paused(id="p-002")
        m = _model_from_pipeline(p)
        assert m.paused is True

    def test_pipeline_to_model_running_paused_flag(self):
        """RUNNING 状态的 Pipeline 转换后 paused 列为 False。"""
        p = PipelineFactory.running(id="p-003")
        m = _model_from_pipeline(p)
        assert m.paused is False

    def test_pipeline_to_model_idle_paused_flag(self):
        """IDLE 状态的 Pipeline 转换后 paused 列为 False。"""
        p = PipelineFactory.idle(id="p-004")
        m = _model_from_pipeline(p)
        assert m.paused is False

    def test_model_to_pipeline_basic(self):
        """PipelineModel 转换为 Pipeline 时字段应对应正确。"""
        m = PipelineModel(
            id="p-010",
            project_id="proj-010",
            name="模型流水线",
            status="running",
            current_stage="collect",
            progress=0.75,
            agents=["agent-1"],
            task_ids=["task-1", "task-2"],
            context={"key": "value"},
            logs=[],
            team_config={"strategy": "sequential"},
            agent_roles={"agent-1": "研究员"},
            stages=[{"key": "collect", "label": "收集"}],
            paused=False,
            stop_requested=False,
            created_at=datetime.now(),
        )
        p = _pipeline_from_model(m)

        assert p.id == "p-010"
        assert p.project_id == "proj-010"
        assert p.name == "模型流水线"
        assert p.status == PipelineStatus.RUNNING
        assert p.current_stage == "collect"
        assert p.progress == 0.75
        assert p.agents == ["agent-1"]
        assert p.task_ids == ["task-1", "task-2"]
        assert p.context == {"key": "value"}

    # -- paused 列兼容性 --

    def test_model_with_paused_true_and_status_running_fixed(self):
        """DB 中 paused=True 但 status='running' → 加载时自动修正为 PAUSED。"""
        m = PipelineModel(
            id="p-100",
            project_id="proj-100",
            name="不一致数据",
            status="running",
            paused=True,  # 不一致！
        )
        p = _pipeline_from_model(m)
        assert p.status == PipelineStatus.PAUSED, (
            "paused=True 但 status=running 时，应以 paused 为准修正为 PAUSED"
        )

    def test_model_with_paused_false_and_status_paused_kept(self):
        """DB 中 paused=False 但 status='paused' → 以 status 为准。"""
        m = PipelineModel(
            id="p-101",
            project_id="proj-101",
            name="正常暂停数据",
            status="paused",
            paused=False,
        )
        p = _pipeline_from_model(m)
        # status 优先，paused=False 不做反向修正
        assert p.status == PipelineStatus.PAUSED

    def test_model_with_paused_true_and_status_paused_consistent(self):
        """DB 中 paused=True 且 status='paused' → 一致，保持 PAUSED。"""
        m = PipelineModel(
            id="p-102",
            project_id="proj-102",
            name="一致暂停数据",
            status="paused",
            paused=True,
        )
        p = _pipeline_from_model(m)
        assert p.status == PipelineStatus.PAUSED

    def test_model_with_paused_false_and_status_running_consistent(self):
        """正常一致数据不修改。"""
        m = PipelineModel(
            id="p-103",
            project_id="proj-103",
            name="正常数据",
            status="running",
            paused=False,
        )
        p = _pipeline_from_model(m)
        assert p.status == PipelineStatus.RUNNING

    # -- 日志截断 --

    def test_logs_preserved_in_conversion(self):
        """Pipeline 日志应完整保留在转换中。"""
        p = PipelineFactory.create(id="p-log")
        p.add_log("test", "测试日志1")
        p.add_log("test", "测试日志2")

        m = _model_from_pipeline(p)
        assert len(m.logs) == 2
        assert m.logs[0]["message"] == "测试日志1"
        assert m.logs[1]["message"] == "测试日志2"

    # -- 空字段默认值 --

    def test_empty_agents_default_to_list(self):
        m = PipelineModel(id="p-empty", project_id="proj-empty", status="idle")
        p = _pipeline_from_model(m)
        assert p.agents == []

    def test_empty_stages_default_to_list(self):
        m = PipelineModel(id="p-empty", project_id="proj-empty", status="idle")
        p = _pipeline_from_model(m)
        assert p.stages == []

    def test_empty_context_default_to_dict(self):
        m = PipelineModel(id="p-empty", project_id="proj-empty", status="idle")
        p = _pipeline_from_model(m)
        assert p.context == {}


# ========== PipelineFactory 验证 ==========


class TestPipelineFactory:
    """验证测试工厂方法生成的对象。"""

    def test_factory_idle_defaults(self):
        p = PipelineFactory.idle()
        assert p.status == PipelineStatus.IDLE
        assert p.id == "factory-pipeline-001"

    def test_factory_running_status(self):
        p = PipelineFactory.running()
        assert p.status == PipelineStatus.RUNNING

    def test_factory_paused_status(self):
        p = PipelineFactory.paused()
        assert p.status == PipelineStatus.PAUSED

    def test_factory_custom_params(self):
        p = PipelineFactory.create(
            id="custom-id",
            name="自定义",
            status=PipelineStatus.FAILED,
            agents=["a", "b"],
            stages=[{"key": "s1"}],
        )
        assert p.id == "custom-id"
        assert p.name == "自定义"
        assert p.status == PipelineStatus.FAILED
        assert p.agents == ["a", "b"]
        assert p.stages == [{"key": "s1"}]
