"""全局测试 fixtures。

提供跨测试模块共享的 Pipeline、Project、Agent 等工厂方法。
"""

import pytest

from app.services.collaboration.pipeline_orchestrator import (
    Pipeline,
    PipelineStatus,
    PipelineOrchestrator,
)


@pytest.fixture
def sample_pipeline():
    """创建一个处于 IDLE 状态的基础 Pipeline。"""
    p = Pipeline()
    p.id = "test-pipeline-001"
    p.project_id = "test-project-001"
    p.name = "测试流水线"
    return p


@pytest.fixture
def running_pipeline():
    """创建一个处于 RUNNING 状态的 Pipeline。"""
    p = Pipeline()
    p.id = "test-pipeline-002"
    p.project_id = "test-project-002"
    p.name = "运行中流水线"
    p.status = PipelineStatus.RUNNING
    return p


@pytest.fixture
def paused_pipeline():
    """创建一个处于 PAUSED 状态的 Pipeline。"""
    p = Pipeline()
    p.id = "test-pipeline-003"
    p.project_id = "test-project-003"
    p.name = "已暂停流水线"
    p.status = PipelineStatus.PAUSED
    return p


@pytest.fixture
def orchestrator():
    """创建一个未初始化的 PipelineOrchestrator。"""
    return PipelineOrchestrator()
