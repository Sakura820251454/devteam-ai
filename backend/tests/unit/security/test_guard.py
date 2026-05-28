"""安全守卫单元测试。

测试 SecurityGuard 的权限检查、风险分级、Kill Switch、断路器。
纯逻辑测试，不依赖 LLM 或数据库。
"""

import pytest

from app.services.security.guard import (
    SecurityGuard,
    OperationType,
    EmergencyStopReason,
    OPERATION_RISK_MAP,
)
from app.models.task import RiskLevel


# ========== 操作→风险级别映射 ==========


class TestOperationRiskMap:
    """OPERATION_RISK_MAP 完整性测试。"""

    def test_all_operations_have_risk_level(self):
        """每个 OperationType 枚举值都有对应的风险级别映射。"""
        for op in OperationType:
            assert op in OPERATION_RISK_MAP, f"OperationType.{op.name} 缺少风险级别映射"

    def test_low_risk_operations(self):
        """低风险操作：查询、生成文档、读取配置 — 自动执行。"""
        low_ops = [
            OperationType.QUERY_DATA,
            OperationType.GENERATE_DOCS,
            OperationType.READ_CONFIG,
            OperationType.VIEW_METRICS,
        ]
        for op in low_ops:
            assert OPERATION_RISK_MAP[op] == RiskLevel.LOW, f"{op.value} 应为 LOW 风险"

    def test_medium_risk_operations(self):
        """中风险操作：修改配置、生成代码 — Agent 自审。"""
        medium_ops = [
            OperationType.MODIFY_CONFIG,
            OperationType.GENERATE_CODE,
            OperationType.UPDATE_TASK,
            OperationType.CALL_EXTERNAL_API,
        ]
        for op in medium_ops:
            assert OPERATION_RISK_MAP[op] == RiskLevel.MEDIUM, f"{op.value} 应为 MEDIUM 风险"

    def test_high_risk_operations(self):
        """高风险操作：删除数据、部署代码 — 强制人工审批。"""
        high_ops = [
            OperationType.DELETE_DATA,
            OperationType.MODIFY_SYSTEM_PROMPT,
            OperationType.DEPLOY_CODE,
            OperationType.CHANGE_PERMISSIONS,
        ]
        for op in high_ops:
            assert OPERATION_RISK_MAP[op] == RiskLevel.HIGH, f"{op.value} 应为 HIGH 风险"

    def test_critical_risk_operations(self):
        """CRITICAL 操作：修改安全模块、删除审计日志 — 宪法层禁止。"""
        critical_ops = [
            OperationType.MODIFY_SECURITY_MODULE,
            OperationType.DELETE_AUDIT_LOG,
            OperationType.MODIFY_CONSTITUTION,
        ]
        for op in critical_ops:
            assert OPERATION_RISK_MAP[op] == RiskLevel.CRITICAL, f"{op.value} 应为 CRITICAL 风险"


# ========== SecurityGuard 核心方法 ==========


class TestRiskLevelCheck:
    """get_risk_level / requires_human_approval 测试。"""

    @pytest.fixture
    def guard(self):
        return SecurityGuard()

    @pytest.mark.parametrize("op,expected", [
        (OperationType.QUERY_DATA, RiskLevel.LOW),
        (OperationType.GENERATE_CODE, RiskLevel.MEDIUM),
        (OperationType.DEPLOY_CODE, RiskLevel.HIGH),
        (OperationType.MODIFY_SECURITY_MODULE, RiskLevel.CRITICAL),
    ])
    def test_get_risk_level(self, guard, op, expected):
        assert guard.get_risk_level(op) == expected

    @pytest.mark.parametrize("op,needs_approval", [
        (OperationType.QUERY_DATA, False),
        (OperationType.GENERATE_DOCS, False),
        (OperationType.GENERATE_CODE, False),
        (OperationType.DELETE_DATA, True),
        (OperationType.DEPLOY_CODE, True),
        (OperationType.MODIFY_SECURITY_MODULE, True),
    ])
    def test_requires_human_approval(self, guard, op, needs_approval):
        assert guard.requires_human_approval(op) == needs_approval


class TestOperationAllowed:
    """is_operation_allowed 测试。"""

    @pytest.fixture
    def guard(self):
        return SecurityGuard()

    # -- 正常情况 --

    def test_low_risk_operation_allowed_by_default(self, guard):
        allowed, reason = guard.is_operation_allowed(OperationType.QUERY_DATA, agent_id="agent-1")
        assert allowed is True
        assert reason == "ok"

    def test_medium_risk_operation_allowed_by_default(self, guard):
        """中风险操作默认允许（审批由 check_and_require_approval 处理）。"""
        allowed, reason = guard.is_operation_allowed(OperationType.GENERATE_CODE, agent_id="agent-1")
        assert allowed is True

    # -- Kill Switch 阻塞 --

    def test_kill_switch_blocks_all_operations(self, guard):
        guard._emergency.active = True
        guard._emergency.reason = EmergencyStopReason.HUMAN_TRIGGERED
        allowed, reason = guard.is_operation_allowed(OperationType.QUERY_DATA, agent_id="agent-1")
        assert allowed is False
        assert "紧急停止" in reason

    # -- 断路器隔离 --

    def test_isolated_agent_is_blocked(self, guard):
        guard._isolated_agents.add("agent-bad")
        allowed, reason = guard.is_operation_allowed(OperationType.QUERY_DATA, agent_id="agent-bad")
        assert allowed is False
        assert "断路器" in reason or "隔离" in reason

    def test_non_isolated_agent_still_works(self, guard):
        guard._isolated_agents.add("agent-bad")
        allowed, reason = guard.is_operation_allowed(OperationType.QUERY_DATA, agent_id="agent-good")
        assert allowed is True

    # -- 宪法层禁止（CRITICAL） --

    @pytest.mark.parametrize("critical_op", [
        OperationType.MODIFY_SECURITY_MODULE,
        OperationType.DELETE_AUDIT_LOG,
        OperationType.MODIFY_CONSTITUTION,
    ])
    def test_critical_operations_are_constitutionally_blocked(self, guard, critical_op):
        allowed, reason = guard.is_operation_allowed(critical_op, agent_id="agent-1")
        assert allowed is False
        assert "宪法" in reason or "最高风险" in reason or "禁止" in reason

    # -- 权限检查 --

    def test_agent_without_permission_is_blocked(self, guard):
        guard._agent_permissions["agent-1"] = {OperationType.QUERY_DATA}
        allowed, reason = guard.is_operation_allowed(OperationType.GENERATE_CODE, agent_id="agent-1")
        assert allowed is False
        assert "没有" in reason or "权限" in reason

    def test_agent_with_permission_passes(self, guard):
        guard._agent_permissions["agent-1"] = {OperationType.QUERY_DATA, OperationType.GENERATE_CODE}
        allowed, reason = guard.is_operation_allowed(OperationType.GENERATE_CODE, agent_id="agent-1")
        assert allowed is True


class TestCheckAndRequireApproval:
    """check_and_require_approval 完整检查测试。"""

    @pytest.fixture
    def guard(self):
        return SecurityGuard()

    def test_low_risk_no_approval(self, guard):
        result = guard.check_and_require_approval(OperationType.GENERATE_DOCS, agent_id="agent-1")
        assert result["allowed"] is True
        assert result["requires_approval"] is False
        assert result["risk_level"] == "low"

    def test_high_risk_requires_approval(self, guard):
        result = guard.check_and_require_approval(OperationType.DEPLOY_CODE, agent_id="agent-1")
        assert result["allowed"] is True
        assert result["requires_approval"] is True
        assert result["risk_level"] == "high"

    def test_critical_blocked(self, guard):
        result = guard.check_and_require_approval(OperationType.MODIFY_SECURITY_MODULE, agent_id="agent-1")
        assert result["allowed"] is False

    def test_kill_switch_blocked(self, guard):
        guard._emergency.active = True
        result = guard.check_and_require_approval(OperationType.QUERY_DATA, agent_id="agent-1")
        assert result["allowed"] is False

    def test_medium_risk_allowed_without_approval(self, guard):
        result = guard.check_and_require_approval(OperationType.GENERATE_CODE, agent_id="agent-1")
        assert result["allowed"] is True
        assert result["requires_approval"] is False
        assert result["risk_level"] == "medium"


# ========== 权限管理 ==========


class TestPermissionManagement:
    """grant / revoke / get 权限管理测试。"""

    @pytest.fixture
    def guard(self):
        return SecurityGuard()

    def test_grant_permission(self, guard):
        guard.grant_permission("agent-1", [OperationType.QUERY_DATA])
        assert "query_data" in guard.get_agent_permissions("agent-1")

    def test_grant_multiple_permissions(self, guard):
        guard.grant_permission("agent-1", [OperationType.QUERY_DATA, OperationType.GENERATE_CODE])
        perms = guard.get_agent_permissions("agent-1")
        assert "query_data" in perms
        assert "generate_code" in perms

    def test_grant_accumulates(self, guard):
        guard.grant_permission("agent-1", [OperationType.QUERY_DATA])
        guard.grant_permission("agent-1", [OperationType.GENERATE_CODE])
        perms = guard.get_agent_permissions("agent-1")
        assert len(perms) == 2

    def test_revoke_permission(self, guard):
        guard.grant_permission("agent-1", [OperationType.QUERY_DATA, OperationType.GENERATE_CODE])
        guard.revoke_permission("agent-1", OperationType.QUERY_DATA)
        perms = guard.get_agent_permissions("agent-1")
        assert "query_data" not in perms
        assert "generate_code" in perms

    def test_revoke_nonexistent_agent_no_error(self, guard):
        """撤销不存在的 Agent 权限不应报错。"""
        guard.revoke_permission("no-such-agent", OperationType.QUERY_DATA)

    def test_get_permissions_unknown_agent_returns_empty(self, guard):
        assert guard.get_agent_permissions("no-such-agent") == []

    @pytest.mark.parametrize("agent_type,expected_ops", [
        ("product_manager", ["query_data", "generate_docs", "update_task"]),
        ("architect", ["modify_config", "generate_code"]),
        ("backend_developer", ["generate_code", "call_external_api"]),
        ("frontend_developer", ["generate_code", "update_task"]),
        ("tester", ["generate_docs", "update_task"]),
        ("devops", ["deploy_code", "modify_config"]),
    ])
    def test_set_default_permissions(self, guard, agent_type, expected_ops):
        guard.set_default_permissions("agent-1", agent_type)
        perms = guard.get_agent_permissions("agent-1")
        for op in expected_ops:
            assert op in perms, f"{agent_type} 应有 {op} 权限"

    def test_unknown_agent_type_gets_minimal_perms(self, guard):
        guard.set_default_permissions("agent-1", "unknown_role")
        perms = guard.get_agent_permissions("agent-1")
        assert len(perms) > 0  # 至少有一些基本权限


# ========== Kill Switch ==========


class TestKillSwitch:
    """Kill Switch 状态管理测试。"""

    @pytest.fixture
    def guard(self):
        return SecurityGuard()

    def test_is_emergency_defaults_false(self, guard):
        assert guard.is_emergency is False

    def test_emergency_state_defaults_inactive(self, guard):
        assert guard.emergency_state == {"active": False}

    def test_emergency_state_after_manual_activation(self, guard):
        """手动设置紧急状态后，emergency_state 应反映当前值。"""
        guard._emergency.active = True
        guard._emergency.reason = EmergencyStopReason.HUMAN_TRIGGERED
        guard._emergency.triggered_by = "admin"

        state = guard.emergency_state
        assert state["active"] is True
        assert state["reason"] == "human_triggered"
        assert state["triggered_by"] == "admin"

    def test_emergency_stop_sets_state(self):
        """emergency_stop 应有异步方法（此处验证同步状态变化前逻辑）。"""
        guard = SecurityGuard()
        # 验证初始状态
        assert guard.is_emergency is False
        # 手动激活（绕过需要 mock 的异步广播）
        guard._emergency.active = True
        guard._emergency.reason = EmergencyStopReason.HUMAN_TRIGGERED
        assert guard.is_emergency is True

    def test_emergency_reset_clears_state(self):
        guard = SecurityGuard()
        guard._emergency.active = True
        guard._emergency.reason = EmergencyStopReason.HUMAN_TRIGGERED
        # 重置
        guard._emergency.active = False
        guard._emergency.reason = None
        assert guard.is_emergency is False
        assert guard.emergency_state == {"active": False}


# ========== 断路器 ==========


class TestCircuitBreaker:
    """断路器逻辑测试（不触发外部调用）。"""

    @pytest.fixture
    def guard(self):
        return SecurityGuard()

    def test_initial_error_stats_empty(self, guard):
        stats = guard.get_agent_error_stats("agent-1")
        assert stats == {}

    @pytest.mark.asyncio
    async def test_record_successful_operations(self, guard):
        for _ in range(5):
            await guard.record_operation_result("agent-1", OperationType.QUERY_DATA, success=True)

        stats = guard.get_agent_error_stats("agent-1")
        assert stats["query_data"]["total"] == 5
        assert stats["query_data"]["errors"] == 0
        assert stats["query_data"]["error_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_record_mixed_operations(self, guard):
        await guard.record_operation_result("agent-1", OperationType.GENERATE_CODE, success=True)
        await guard.record_operation_result("agent-1", OperationType.GENERATE_CODE, success=False)
        await guard.record_operation_result("agent-1", OperationType.GENERATE_CODE, success=True)
        await guard.record_operation_result("agent-1", OperationType.GENERATE_CODE, success=True)
        await guard.record_operation_result("agent-1", OperationType.GENERATE_CODE, success=True)

        stats = guard.get_agent_error_stats("agent-1")
        assert stats["generate_code"]["total"] == 5
        assert stats["generate_code"]["errors"] == 1
        assert stats["generate_code"]["error_rate"] == 0.2

    @pytest.mark.asyncio
    async def test_circuit_breaker_triggers_on_high_error_rate(self, guard):
        """错误率 > 30% 且 >=5 次操作时触发断路器。"""
        for _ in range(3):
            await guard.record_operation_result("agent-bad", OperationType.GENERATE_CODE, success=True)
        for _ in range(3):
            await guard.record_operation_result("agent-bad", OperationType.GENERATE_CODE, success=False)

        # 6次操作，3次失败 = 50% 错误率，应触发断路器
        stats = guard.get_agent_error_stats("agent-bad")
        assert stats["generate_code"]["error_rate"] > 0.3
        # 断路器触发后 agent 被隔离
        assert "agent-bad" in guard._isolated_agents

    @pytest.mark.asyncio
    async def test_circuit_breaker_not_triggered_below_threshold(self, guard):
        """错误率低时不触发断路器。"""
        for _ in range(4):
            await guard.record_operation_result("agent-ok", OperationType.QUERY_DATA, success=True)
        await guard.record_operation_result("agent-ok", OperationType.QUERY_DATA, success=False)

        # 5次操作，1次失败 = 20% 错误率
        assert "agent-ok" not in guard._isolated_agents

    @pytest.mark.asyncio
    async def test_circuit_breaker_not_triggered_under_min_ops(self, guard):
        """操作次数不足时不触发。"""
        await guard.record_operation_result("agent-new", OperationType.QUERY_DATA, success=False)
        await guard.record_operation_result("agent-new", OperationType.QUERY_DATA, success=False)

        # 只有2次，即使100%失败也不应触发
        assert "agent-new" not in guard._isolated_agents

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker_clears_isolation(self, guard):
        guard._isolated_agents.add("agent-bad")
        guard._error_counters["agent-bad:query_data"] = 5
        guard._operation_counters["agent-bad:query_data"] = 10

        result = await guard.reset_circuit_breaker("agent-bad")
        assert result is True
        assert "agent-bad" not in guard._isolated_agents
        assert guard._error_counters["agent-bad:query_data"] == 0
        assert guard._operation_counters["agent-bad:query_data"] == 0

    @pytest.mark.asyncio
    async def test_different_agents_have_independent_counters(self, guard):
        await guard.record_operation_result("agent-1", OperationType.QUERY_DATA, success=False)
        await guard.record_operation_result("agent-2", OperationType.QUERY_DATA, success=True)

        stats_1 = guard.get_agent_error_stats("agent-1")
        stats_2 = guard.get_agent_error_stats("agent-2")
        assert stats_1["query_data"]["errors"] == 1
        assert stats_2["query_data"]["errors"] == 0


# ========== 宪法原则 ==========


class TestConstitutionalPrinciples:
    """宪法原则不可违。"""

    def test_principles_are_defined(self, guard=None):
        guard = guard or SecurityGuard()
        assert len(guard.CONSTITUTIONAL_PRINCIPLES) == 4
        for principle in guard.CONSTITUTIONAL_PRINCIPLES:
            assert len(principle) > 5, f"宪法原则不应为空: {principle!r}"
