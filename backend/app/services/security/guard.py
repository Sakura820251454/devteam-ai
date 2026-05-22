"""
安全守卫系统 — 风险分级 + 权限控制 + 全局 Kill Switch

参照多智能体协作报告的安全与对齐维度设计：
- 风险分级：LOW/MEDIUM/HIGH/CRITICAL，不同级别不同审批策略
- 最小权限：每个 Agent 和操作都有权限约束
- Kill Switch：全局紧急停止，冻结所有 Agent 活动
- 断路器：错误率超阈值自动隔离
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field

from app.models.task import RiskLevel


class OperationType(str, Enum):
    """操作类型定义"""
    # 低风险 — 自动执行
    QUERY_DATA = "query_data"
    GENERATE_DOCS = "generate_docs"
    READ_CONFIG = "read_config"
    VIEW_METRICS = "view_metrics"
    # 中风险 — Agent 自审
    MODIFY_CONFIG = "modify_config"
    GENERATE_CODE = "generate_code"
    UPDATE_TASK = "update_task"
    CALL_EXTERNAL_API = "call_external_api"
    # 高风险 — 强制人工审批
    DELETE_DATA = "delete_data"
    MODIFY_SYSTEM_PROMPT = "modify_system_prompt"
    DEPLOY_CODE = "deploy_code"
    CHANGE_PERMISSIONS = "change_permissions"
    # 最高风险 — 禁止
    MODIFY_SECURITY_MODULE = "modify_security_module"
    DELETE_AUDIT_LOG = "delete_audit_log"
    MODIFY_CONSTITUTION = "modify_constitution"


# 操作→风险级别映射
OPERATION_RISK_MAP: Dict[OperationType, RiskLevel] = {
    OperationType.QUERY_DATA: RiskLevel.LOW,
    OperationType.GENERATE_DOCS: RiskLevel.LOW,
    OperationType.READ_CONFIG: RiskLevel.LOW,
    OperationType.VIEW_METRICS: RiskLevel.LOW,
    OperationType.MODIFY_CONFIG: RiskLevel.MEDIUM,
    OperationType.GENERATE_CODE: RiskLevel.MEDIUM,
    OperationType.UPDATE_TASK: RiskLevel.MEDIUM,
    OperationType.CALL_EXTERNAL_API: RiskLevel.MEDIUM,
    OperationType.DELETE_DATA: RiskLevel.HIGH,
    OperationType.MODIFY_SYSTEM_PROMPT: RiskLevel.HIGH,
    OperationType.DEPLOY_CODE: RiskLevel.HIGH,
    OperationType.CHANGE_PERMISSIONS: RiskLevel.HIGH,
    OperationType.MODIFY_SECURITY_MODULE: RiskLevel.CRITICAL,
    OperationType.DELETE_AUDIT_LOG: RiskLevel.CRITICAL,
    OperationType.MODIFY_CONSTITUTION: RiskLevel.CRITICAL,
}


@dataclass
class OperationPermission:
    """操作权限定义"""
    operation: OperationType
    risk_level: RiskLevel
    requires_approval: bool = False
    allowed_roles: Set[str] = field(default_factory=set)
    max_retries: int = 0  # CRITICAL 操作不允许重试


class EmergencyStopReason(str, Enum):
    HUMAN_TRIGGERED = "human_triggered"
    CIRCUIT_BREAKER = "circuit_breaker"
    CRITICAL_VIOLATION = "critical_violation"
    RESOURCE_EXHAUSTED = "resource_exhausted"


@dataclass
class EmergencyState:
    active: bool = False
    reason: Optional[EmergencyStopReason] = None
    triggered_by: str = ""
    triggered_at: Optional[datetime] = None
    message: str = ""


class SecurityGuard:
    """
    安全守卫 — 系统的安全中枢

    宪法层（Constitutional Layer）：硬编码不可违背的核心原则
    - 不得修改安全模块自身
    - 不得删除审计日志
    - Kill Switch 优先级最高
    """

    # 宪法原则 — 任何操作都不能绕过
    CONSTITUTIONAL_PRINCIPLES = [
        "安全模块自身不可被修改",
        "审计日志不可被删除或篡改",
        "Kill Switch 的优先级高于一切操作",
        "人类审批链不可被自动化绕过",
    ]

    def __init__(self):
        # 全局紧急停止状态
        self._emergency: EmergencyState = EmergencyState()
        # Agent 权限配置
        self._agent_permissions: Dict[str, Set[OperationType]] = {}
        # 断路器配置
        self._circuit_breaker_threshold: float = 0.3  # 错误率 > 30% 触发
        self._error_counters: Dict[str, int] = {}
        self._operation_counters: Dict[str, int] = {}
        self._isolated_agents: Set[str] = set()
        self._lock = asyncio.Lock()

    # ==================== 权限检查 ====================

    def get_risk_level(self, operation: OperationType) -> RiskLevel:
        """获取操作的风险级别"""
        return OPERATION_RISK_MAP.get(operation, RiskLevel.MEDIUM)

    def requires_human_approval(self, operation: OperationType) -> bool:
        """检查操作是否需要人工审批"""
        risk = self.get_risk_level(operation)
        return risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def is_operation_allowed(
        self,
        operation: OperationType,
        agent_id: str = "system",
        agent_role: str = "unknown"
    ) -> tuple[bool, str]:
        """
        检查操作是否允许执行

        返回: (是否允许, 原因)
        """
        # 1. Kill Switch 检查 — 最高优先级
        if self._emergency.active:
            return False, f"全局紧急停止已激活: {self._emergency.reason}"

        # 2. 断路器检查 — 隔离的 Agent
        if agent_id in self._isolated_agents:
            return False, f"Agent {agent_id} 已被断路器隔离"

        # 3. 宪法层检查 — 绝对禁止的操作
        risk = self.get_risk_level(operation)
        if risk == RiskLevel.CRITICAL:
            return False, f"操作 {operation.value} 属于最高风险级别，已被宪法层禁止"

        # 4. 权限检查 — Agent 是否有此操作权限
        if agent_id in self._agent_permissions:
            allowed_ops = self._agent_permissions[agent_id]
            if operation not in allowed_ops:
                return False, f"Agent {agent_id} 没有 {operation.value} 操作权限"

        return True, "ok"

    def check_and_require_approval(
        self,
        operation: OperationType,
        agent_id: str = "system"
    ) -> Dict[str, Any]:
        """
        完整检查：权限 + 审批需求
        返回操作是否可执行、是否需要审批、原因
        """
        allowed, reason = self.is_operation_allowed(operation, agent_id)
        if not allowed:
            return {
                "allowed": False,
                "requires_approval": False,
                "risk_level": self.get_risk_level(operation).value,
                "reason": reason
            }

        needs_approval = self.requires_human_approval(operation)
        risk = self.get_risk_level(operation)

        return {
            "allowed": True,
            "requires_approval": needs_approval,
            "risk_level": risk.value,
            "reason": "ok" if not needs_approval else f"操作 {operation.value} 需要人工审批 (风险级别: {risk.value})"
        }

    # ==================== Agent 权限管理 ====================

    def grant_permission(self, agent_id: str, operations: List[OperationType]):
        """授予 Agent 操作权限"""
        if agent_id not in self._agent_permissions:
            self._agent_permissions[agent_id] = set()
        self._agent_permissions[agent_id].update(operations)

    def revoke_permission(self, agent_id: str, operation: OperationType):
        """撤销 Agent 特定操作权限"""
        if agent_id in self._agent_permissions:
            self._agent_permissions[agent_id].discard(operation)

    def get_agent_permissions(self, agent_id: str) -> List[str]:
        """获取 Agent 的权限列表"""
        perms = self._agent_permissions.get(agent_id, set())
        return [op.value for op in perms]

    def set_default_permissions(self, agent_id: str, agent_type: str):
        """根据 Agent 类型设置默认权限"""
        default_perms = {
            "product_manager": [OperationType.QUERY_DATA, OperationType.GENERATE_DOCS,
                               OperationType.READ_CONFIG, OperationType.VIEW_METRICS,
                               OperationType.UPDATE_TASK],
            "architect": [OperationType.QUERY_DATA, OperationType.GENERATE_DOCS,
                         OperationType.READ_CONFIG, OperationType.VIEW_METRICS,
                         OperationType.MODIFY_CONFIG, OperationType.GENERATE_CODE],
            "backend_developer": [OperationType.QUERY_DATA, OperationType.GENERATE_CODE,
                                 OperationType.UPDATE_TASK, OperationType.CALL_EXTERNAL_API,
                                 OperationType.READ_CONFIG],
            "frontend_developer": [OperationType.QUERY_DATA, OperationType.GENERATE_CODE,
                                  OperationType.UPDATE_TASK, OperationType.READ_CONFIG],
            "tester": [OperationType.QUERY_DATA, OperationType.GENERATE_DOCS,
                      OperationType.VIEW_METRICS, OperationType.UPDATE_TASK],
            "devops": [OperationType.QUERY_DATA, OperationType.MODIFY_CONFIG,
                      OperationType.DEPLOY_CODE, OperationType.VIEW_METRICS,
                      OperationType.CALL_EXTERNAL_API],
        }
        perms = default_perms.get(agent_type, [OperationType.QUERY_DATA, OperationType.VIEW_METRICS])
        self._agent_permissions[agent_id] = set(perms)

    # ==================== Kill Switch ====================

    @property
    def is_emergency(self) -> bool:
        return self._emergency.active

    @property
    def emergency_state(self) -> Dict[str, Any]:
        if not self._emergency.active:
            return {"active": False}
        return {
            "active": True,
            "reason": self._emergency.reason.value if self._emergency.reason else None,
            "triggered_by": self._emergency.triggered_by,
            "triggered_at": self._emergency.triggered_at.isoformat() if self._emergency.triggered_at else None,
            "message": self._emergency.message,
            "isolated_agents": list(self._isolated_agents)
        }

    async def emergency_stop(
        self,
        triggered_by: str,
        reason: EmergencyStopReason = EmergencyStopReason.HUMAN_TRIGGERED,
        message: str = ""
    ) -> Dict[str, Any]:
        """全局紧急停止 — 立即冻结所有 Agent 活动"""
        async with self._lock:
            self._emergency = EmergencyState(
                active=True,
                reason=reason,
                triggered_by=triggered_by,
                triggered_at=datetime.now(),
                message=message or f"紧急停止由 {triggered_by} 触发"
            )

            # 通知外部系统
            from app.services.collaboration.message_bus import message_bus, Message, MessageType
            from app.services.agent.agent_executor import agent_executor

            msg = Message(
                sender_id="security_guard",
                sender_name="SecurityGuard",
                content=f"🔴 全局紧急停止！原因: {reason.value}\n{self._emergency.message}",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)

            # 暂停所有 Agent 执行
            await agent_executor.pause_all()

            return self.emergency_state

    async def emergency_reset(self, triggered_by: str) -> Dict[str, Any]:
        """重置紧急状态"""
        async with self._lock:
            if not self._emergency.active:
                return {"active": False, "message": "当前没有紧急状态"}

            from app.services.collaboration.message_bus import message_bus, Message, MessageType

            self._emergency = EmergencyState()

            msg = Message(
                sender_id="security_guard",
                sender_name="SecurityGuard",
                content=f"🟢 紧急状态已由 {triggered_by} 解除",
                message_type=MessageType.SYSTEM
            )
            await message_bus.broadcast(msg)

            return {"active": False, "message": "紧急状态已解除"}

    # ==================== 断路器 ====================

    async def record_operation_result(
        self,
        agent_id: str,
        operation: OperationType,
        success: bool
    ):
        """记录操作结果，用于断路器判断"""
        async with self._lock:
            key = f"{agent_id}:{operation.value}"
            self._operation_counters[key] = self._operation_counters.get(key, 0) + 1
            if not success:
                self._error_counters[key] = self._error_counters.get(key, 0) + 1
            else:
                self._error_counters.setdefault(key, 0)

            # 检查是否需要触发断路器
            total = self._operation_counters[key]
            errors = self._error_counters.get(key, 0)
            if total >= 5:  # 至少 5 次操作才评估
                error_rate = errors / total
                if error_rate > self._circuit_breaker_threshold:
                    await self._isolate_agent(agent_id, f"错误率 {error_rate:.1%} 超过阈值")

    async def _isolate_agent(self, agent_id: str, reason: str):
        """隔离 Agent — 断路器触发"""
        if agent_id in self._isolated_agents:
            return
        self._isolated_agents.add(agent_id)

        from app.services.collaboration.message_bus import message_bus, Message, MessageType
        from app.services.agent.agent_executor import agent_executor

        task_id = agent_executor.get_agent_current_task(agent_id)
        if task_id:
            await agent_executor.cancel_execution(task_id)

        msg = Message(
            sender_id="security_guard",
            sender_name="SecurityGuard",
            content=f"⚠️ Agent {agent_id} 已被断路器隔离: {reason}",
            message_type=MessageType.SYSTEM
        )
        await message_bus.broadcast(msg)

    async def reset_circuit_breaker(self, agent_id: str) -> bool:
        """重置断路器的错误计数"""
        if agent_id in self._isolated_agents:
            self._isolated_agents.discard(agent_id)
        # 清除该 Agent 的所有计数器
        prefix = f"{agent_id}:"
        keys_to_clear = [k for k in self._error_counters if k.startswith(prefix)]
        for k in keys_to_clear:
            self._error_counters[k] = 0
            self._operation_counters[k] = 0
        return True

    def get_agent_error_stats(self, agent_id: str) -> Dict[str, Any]:
        """获取 Agent 错误统计"""
        prefix = f"{agent_id}:"
        stats = {}
        for key in self._operation_counters:
            if key.startswith(prefix):
                op_name = key.split(":", 1)[1]
                total = self._operation_counters.get(key, 0)
                errors = self._error_counters.get(key, 0)
                stats[op_name] = {
                    "total": total,
                    "errors": errors,
                    "error_rate": errors / total if total > 0 else 0.0,
                    "circuit_broken": agent_id in self._isolated_agents
                }
        return stats


# 全局安全守卫
security_guard = SecurityGuard()
