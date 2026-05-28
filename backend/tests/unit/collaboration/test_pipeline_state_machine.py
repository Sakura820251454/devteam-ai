"""Pipeline 状态机单元测试。

测试全部合法/非法状态转移，确保 transition() 方法正确校验。
无需 LLM — 纯状态逻辑测试。
"""

import pytest

from app.services.collaboration.pipeline_orchestrator import (
    Pipeline,
    PipelineStatus,
    PipelineOrchestrator,
    IllegalStateTransition,
    _ALLOWED_TRANSITIONS,
)


@pytest.fixture
def pipeline():
    """创建一个 IDLE 状态的空 Pipeline。"""
    p = Pipeline()
    p.id = "test-pipeline"
    p.project_id = "test-project"
    p.name = "测试流水线"
    return p


@pytest.fixture
def orchestrator():
    """创建一个未初始化的 PipelineOrchestrator（transition 是静态方法，无需 DB）。"""
    return PipelineOrchestrator()


# ========== 合法转移测试 ==========

LEGAL_TRANSITIONS = [
    (PipelineStatus.IDLE, PipelineStatus.RUNNING),
    (PipelineStatus.IDLE, PipelineStatus.FAILED),
    (PipelineStatus.RUNNING, PipelineStatus.PAUSED),
    (PipelineStatus.RUNNING, PipelineStatus.COMPLETED),
    (PipelineStatus.RUNNING, PipelineStatus.FAILED),
    (PipelineStatus.PAUSED, PipelineStatus.RUNNING),
    (PipelineStatus.PAUSED, PipelineStatus.FAILED),
    (PipelineStatus.FAILED, PipelineStatus.RUNNING),
]


@pytest.mark.parametrize("from_status,to_status", LEGAL_TRANSITIONS)
def test_legal_transition(pipeline, orchestrator, from_status, to_status):
    """合法转移不应抛出异常，且状态应正确更新。"""
    pipeline.status = from_status  # 手动设置初始状态
    orchestrator.transition(pipeline, to_status)
    assert pipeline.status == to_status


# ========== 非法转移测试 ==========

ILLEGAL_TRANSITIONS = [
    (PipelineStatus.IDLE, PipelineStatus.PAUSED),
    (PipelineStatus.IDLE, PipelineStatus.COMPLETED),
    (PipelineStatus.RUNNING, PipelineStatus.IDLE),
    (PipelineStatus.PAUSED, PipelineStatus.IDLE),
    (PipelineStatus.PAUSED, PipelineStatus.COMPLETED),
    (PipelineStatus.COMPLETED, PipelineStatus.RUNNING),
    (PipelineStatus.COMPLETED, PipelineStatus.PAUSED),
    (PipelineStatus.COMPLETED, PipelineStatus.FAILED),
    (PipelineStatus.COMPLETED, PipelineStatus.IDLE),
    (PipelineStatus.IDLE, PipelineStatus.IDLE),    # 禁止自转移
]


@pytest.mark.parametrize("from_status,to_status", ILLEGAL_TRANSITIONS)
def test_illegal_transition_raises(pipeline, orchestrator, from_status, to_status):
    """非法转移应抛出 IllegalStateTransition。"""
    pipeline.status = from_status
    with pytest.raises(IllegalStateTransition):
        orchestrator.transition(pipeline, to_status)
    # 状态应保持不变
    assert pipeline.status == from_status


# ========== 边界情况 ==========

def test_transition_same_status_is_allowed_for_some(pipeline, orchestrator):
    """同一状态的转移应该被拒绝（自转移不在允许集合中）。"""
    for status in PipelineStatus:
        pipeline.status = status
        if status in _ALLOWED_TRANSITIONS.get(status, set()):
            continue  # 跳过合法自转移（如果有的话）
        with pytest.raises(IllegalStateTransition):
            orchestrator.transition(pipeline, status)


def test_transition_logs_on_change(pipeline, orchestrator):
    """状态转移应记录日志。"""
    initial_log_count = len(pipeline.logs)
    orchestrator.transition(pipeline, PipelineStatus.RUNNING)
    # 应新增一条 debug 日志
    assert len(pipeline.logs) > initial_log_count
    assert "状态转移" in pipeline.logs[-1]["message"]


def test_transition_no_log_when_same(pipeline, orchestrator):
    """相同状态的转移不应产生日志（被 transition 方法在修改前检查）。"""
    pipeline.status = PipelineStatus.COMPLETED  # 终态，无允许的转移
    initial_log_count = len(pipeline.logs)
    try:
        orchestrator.transition(pipeline, PipelineStatus.COMPLETED)
    except IllegalStateTransition:
        pass
    assert len(pipeline.logs) == initial_log_count


def test_completed_is_terminal():
    """COMPLETED 状态不可转移到任何其他状态。"""
    assert _ALLOWED_TRANSITIONS[PipelineStatus.COMPLETED] == set()


def test_failed_can_restart():
    """FAILED 状态可以重启（转到 RUNNING）。"""
    assert PipelineStatus.RUNNING in _ALLOWED_TRANSITIONS[PipelineStatus.FAILED]
