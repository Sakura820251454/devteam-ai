"""审计日志单元测试。

测试 WORM 审计日志的哈希链完整性、查询过滤、摘要统计。
纯逻辑 + 临时文件系统测试。
"""

import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest

from app.services.security.audit import (
    AuditAction,
    AuditEntry,
    AuditLogger,
    audit_logger,
)
from app.models.task import RiskLevel


# ========== AuditAction 枚举 ==========


class TestAuditAction:
    """操作类型枚举测试。"""

    def test_all_categories_have_values(self):
        """确保所有审计操作类型都是有效字符串。"""
        for action in AuditAction:
            assert action.value
            assert isinstance(action.value, str)
            assert len(action.value) > 0

    def test_critical_operations_exist(self):
        """关键安全事件类型必须存在。"""
        assert AuditAction.CONSTITUTION_VIOLATION.value == "constitution_violation"
        assert AuditAction.CRITICAL_OPERATION_BLOCKED.value == "critical_operation_blocked"
        assert AuditAction.UNAUTHORIZED_ACCESS.value == "unauthorized_access"


# ========== AuditLogger ==========


class TestAuditLoggerCore:
    """哈希计算和日志写入测试。"""

    def test_compute_hash_deterministic(self):
        """相同的输入产生相同的哈希。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        h1 = logger._compute_hash("test_data", "prev")
        h2 = logger._compute_hash("test_data", "prev")
        assert h1 == h2

    def test_compute_hash_different_inputs(self):
        """不同的输入产生不同的哈希。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        h1 = logger._compute_hash("data_a", "prev")
        h2 = logger._compute_hash("data_b", "prev")
        assert h1 != h2

    def test_compute_hash_different_prev(self):
        """不同的前序哈希产生不同的哈希。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        h1 = logger._compute_hash("data", "prev_a")
        h2 = logger._compute_hash("data", "prev_b")
        assert h1 != h2

    def test_hash_length(self):
        """哈希应为 16 字符的十六进制字符串。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        h = logger._compute_hash("data", "")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_log_returns_audit_entry(self):
        """log() 返回 AuditEntry 对象。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        entry = logger.log(
            action=AuditAction.SYSTEM_START,
            actor="test_user",
            detail="系统启动",
        )
        assert isinstance(entry, AuditEntry)
        assert entry.action == AuditAction.SYSTEM_START
        assert entry.actor == "test_user"
        assert entry.detail == "系统启动"
        assert entry.outcome == "success"
        assert entry.hash  # 不应为空

    def test_log_increments_entry_count(self):
        """每次 log 后 _entry_count 递增。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        assert logger._entry_count == 0
        logger.log(action=AuditAction.SYSTEM_START, actor="a")
        assert logger._entry_count == 1
        logger.log(action=AuditAction.SYSTEM_STOP, actor="a")
        assert logger._entry_count == 2

    def test_log_hash_chain(self):
        """连续日志的哈希构成链（每条依赖前一条）。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        e1 = logger.log(action=AuditAction.SYSTEM_START, actor="a")
        e2 = logger.log(action=AuditAction.SYSTEM_STOP, actor="b")
        # 两条不同条目应有不同哈希
        assert e1.hash != e2.hash

    def test_log_with_all_fields(self):
        """记录包含所有可选字段的日志。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        entry = logger.log(
            action=AuditAction.APPROVAL_GRANTED,
            actor="admin",
            agent_id="agent-1",
            operation="deploy_code",
            risk_level=RiskLevel.HIGH.value,
            target="pipeline-1",
            detail="批准部署操作",
            outcome="success",
            metadata={"key": "value"},
        )
        assert entry.agent_id == "agent-1"
        assert entry.operation == "deploy_code"
        assert entry.risk_level == "high"
        assert entry.target == "pipeline-1"
        assert entry.metadata == {"key": "value"}


class TestAuditLoggerQuery:
    """查询功能测试。"""

    @pytest.fixture
    def populated_logger(self):
        """预填充数据的日志器。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        logger.log(action=AuditAction.SYSTEM_START, actor="system")
        logger.log(action=AuditAction.AGENT_CREATED, actor="admin", agent_id="agent-1")
        logger.log(
            action=AuditAction.PERMISSION_CHECK,
            actor="guard",
            risk_level=RiskLevel.HIGH.value,
            outcome="denied",
        )
        logger.log(action=AuditAction.AGENT_DELETED, actor="admin", agent_id="agent-2")
        logger.log(action=AuditAction.SYSTEM_STOP, actor="system")
        return logger

    def test_query_all(self, populated_logger):
        results = populated_logger.query(limit=100)
        assert len(results) == 5

    def test_query_by_action(self, populated_logger):
        results = populated_logger.query(action=AuditAction.AGENT_CREATED)
        assert len(results) == 1
        assert results[0]["action"] == "agent_created"

    def test_query_by_actor(self, populated_logger):
        results = populated_logger.query(actor="admin")
        assert len(results) == 2

    def test_query_by_agent_id(self, populated_logger):
        results = populated_logger.query(agent_id="agent-1")
        assert len(results) == 1

    def test_query_by_risk_level(self, populated_logger):
        results = populated_logger.query(risk_level=RiskLevel.HIGH.value)
        assert len(results) == 1

    def test_query_by_outcome(self, populated_logger):
        results = populated_logger.query(outcome="denied")
        assert len(results) == 1

    def test_query_limit_and_offset(self, populated_logger):
        results = populated_logger.query(limit=2, offset=0)
        assert len(results) == 2
        results_page2 = populated_logger.query(limit=2, offset=2)
        assert len(results_page2) == 2
        # 分页不应重叠
        ids_page1 = {r["seq"] for r in results}
        ids_page2 = {r["seq"] for r in results_page2}
        assert ids_page1.isdisjoint(ids_page2)

    def test_query_results_sorted_newest_first(self, populated_logger):
        results = populated_logger.query(limit=100)
        # 最新的在前，seq 降序
        seqs = [r["seq"] for r in results]
        assert seqs == sorted(seqs, reverse=True)

    def test_query_empty_logger(self):
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        results = logger.query()
        assert results == []


class TestAuditLoggerTimeQuery:
    """按时间范围查询。"""

    @pytest.fixture
    def logger_with_timespan(self):
        """创建有时间跨度的日志。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        # 使用实际时间戳
        logger.log(action=AuditAction.SYSTEM_START, actor="s")
        return logger

    def test_query_by_time_returns_results(self, logger_with_timespan):
        start = datetime.now() - timedelta(seconds=10)
        end = datetime.now() + timedelta(seconds=10)
        results = logger_with_timespan.query_by_time(start=start, end=end)
        assert len(results) >= 1

    def test_query_by_time_future_range_returns_empty(self, logger_with_timespan):
        start = datetime.now() + timedelta(days=1)
        end = datetime.now() + timedelta(days=2)
        results = logger_with_timespan.query_by_time(start=start, end=end)
        assert results == []


class TestAuditLoggerIntegrity:
    """哈希链完整性校验。"""

    def test_empty_log_passes(self):
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        result = logger.verify_integrity()
        assert result["valid"] is True
        assert result["entries"] == 0

    def test_single_entry_passes(self):
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        logger.log(action=AuditAction.SYSTEM_START, actor="a")
        result = logger.verify_integrity()
        assert result["valid"] is True
        assert result["entries"] == 1

    def test_multiple_entries_pass(self):
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        for i in range(10):
            logger.log(action=AuditAction.AGENT_CREATED, actor=f"agent-{i}")
        result = logger.verify_integrity()
        assert result["valid"] is True
        assert result["entries"] == 10

    def test_tampered_entry_detected(self):
        """篡改某条日志后完整性校验失败。"""
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        logger.log(action=AuditAction.SYSTEM_START, actor="a")
        logger.log(action=AuditAction.SYSTEM_STOP, actor="b")

        # 篡改文件内容
        with open(logger._current_log_file, "a", encoding="utf-8") as f:
            f.write('{"seq": 999, "tampered": true}\n')

        result = logger.verify_integrity()
        assert result["valid"] is False


class TestAuditLoggerSummary:
    """摘要统计测试。"""

    def test_empty_summary(self):
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        summary = logger.get_summary()
        assert summary["total_entries"] == 0
        assert summary["by_action"] == {}
        assert summary["critical_events"] == 0

    def test_summary_counts(self):
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        logger.log(action=AuditAction.SYSTEM_START, actor="a")
        logger.log(action=AuditAction.AGENT_CREATED, actor="a")
        logger.log(
            action=AuditAction.CRITICAL_OPERATION_BLOCKED,
            actor="a",
            risk_level=RiskLevel.CRITICAL.value,
        )

        summary = logger.get_summary()
        assert summary["total_entries"] == 3
        assert summary["by_action"]["system_start"] == 1
        assert summary["by_action"]["agent_created"] == 1
        assert summary["critical_events"] == 1

    def test_get_critical_events(self):
        logger = AuditLogger(log_dir=tempfile.mkdtemp())
        logger.log(action=AuditAction.SYSTEM_START, actor="a")
        logger.log(
            action=AuditAction.TASK_EXECUTED,
            actor="a",
            risk_level=RiskLevel.HIGH.value,
        )
        logger.log(
            action=AuditAction.CONSTITUTION_VIOLATION,
            actor="a",
            risk_level=RiskLevel.CRITICAL.value,
            outcome="denied",
        )

        events = logger.get_critical_events(limit=50)
        # denied outcome + HIGH risk + CRITICAL risk
        assert len(events) >= 2


class TestAuditEntry:
    """AuditEntry 数据类测试。"""

    def test_minimal_entry(self):
        entry = AuditEntry(
            id="001",
            timestamp=datetime.now().isoformat(),
            action=AuditAction.SYSTEM_START,
            actor="system",
        )
        assert entry.id == "001"
        assert entry.action == AuditAction.SYSTEM_START
        assert entry.actor == "system"
        assert entry.outcome == "success"  # 默认值
        assert entry.hash == ""  # 默认空

    def test_full_entry(self):
        entry = AuditEntry(
            id="002",
            timestamp="2026-01-01T00:00:00",
            action=AuditAction.APPROVAL_DENIED,
            actor="guard",
            agent_id="agent-1",
            operation="deploy",
            risk_level="high",
            target="pipeline-1",
            detail="安全规则拒绝",
            outcome="denied",
            metadata={"rule": "no_deploy"},
            hash="abc123",
        )
        assert entry.risk_level == "high"
        assert entry.metadata == {"rule": "no_deploy"}


class TestGlobalAuditLogger:
    """全局 audit_logger 实例。"""

    def test_global_logger_exists(self):
        assert audit_logger is not None
        assert isinstance(audit_logger, AuditLogger)

    def test_global_logger_has_log_dir(self):
        assert audit_logger.log_dir is not None
        assert "audit" in audit_logger.log_dir
