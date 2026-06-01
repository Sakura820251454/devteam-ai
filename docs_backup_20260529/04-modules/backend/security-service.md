# 安全服务模块

**版本**: v2.0
**最后更新**: 2026-05-15

---

## 概述

- **功能定位**：安全守卫 + WORM 审计日志，系统的安全中枢
- **所属层级**：backend
- **代码路径**：`backend/app/services/security/`

---

## 功能特性

- 四级风险分级（LOW/MEDIUM/HIGH/CRITICAL），不同级别不同审批策略
- 操作权限控制（每个 Agent 的允许操作集）
- 全局 Kill Switch（紧急停止，冻结所有 Agent 活动）
- 断路器（检测 Agent 异常 → 清理上下文窗口 → 从记忆系统重新加载 → 通知用户，恢复性修复而非隔离）
- WORM 审计日志（追加写入 + SHA-256 哈希链完整性校验）
- 宪法层（硬编码不可违背的核心原则）

---

## 核心组件

### SecurityGuard (`guard.py`)

安全守卫，系统的安全中枢。所有操作执行前都经过它检查。

| 方法 | 说明 |
|------|------|
| `get_risk_level(operation)` | 获取操作的风险级别 |
| `requires_human_approval(operation)` | 检查是否需要人工审批 |
| `is_operation_allowed(operation, agent_id, agent_role)` | 检查操作是否允许（含 Kill Switch / 断路器 / 宪法层检查） |
| `check_and_require_approval(operation, agent_id)` | 完整检查：权限 + 审批需求 |
| `grant_permission(agent_id, operations)` | 授予 Agent 操作权限 |
| `revoke_permission(agent_id, operation)` | 撤销 Agent 特定权限 |
| `set_default_permissions(agent_id, agent_type)` | 按 Agent 类型设置默认权限 |
| `emergency_stop(triggered_by, reason, message)` | 全局紧急停止 |
| `emergency_reset(triggered_by)` | 解除紧急状态 |
| `record_operation_result(agent_id, operation, success)` | 记录操作结果（断路器数据） |
| `reset_circuit_breaker(agent_id)` | 恢复性修复：清理上下文并重新加载记忆 |

### OperationType 枚举

```python
# 低风险 — 自动执行
QUERY_DATA, GENERATE_DOCS, READ_CONFIG, VIEW_METRICS
# 中风险 — Agent 自审
MODIFY_CONFIG, GENERATE_CODE, UPDATE_TASK, CALL_EXTERNAL_API
# 高风险 — 强制人工审批
DELETE_DATA, MODIFY_SYSTEM_PROMPT, DEPLOY_CODE, CHANGE_PERMISSIONS
# 最高风险 — 禁止
MODIFY_SECURITY_MODULE, DELETE_AUDIT_LOG, MODIFY_CONSTITUTION
```

### AuditLogger (`audit.py`)

WORM（Write Once, Read Many）审计日志器。每行 JSON + SHA-256 哈希链确保完整性。

| 方法 | 说明 |
|------|------|
| `log(action, actor, ...)` | 追加一条审计日志（不可修改） |
| `query(action, actor, agent_id, ...)` | 按条件查询审计日志 |
| `query_by_time(start, end)` | 按时间范围查询 |
| `verify_integrity()` | 哈希链完整性校验 |
| `get_critical_events(limit)` | 获取所有高危/严重事件 |
| `get_summary()` | 审计摘要统计 |

### 宪法原则

安全守卫内置四条不可违背的宪法原则：
1. 安全模块自身不可被修改
2. 审计日志不可被删除或篡改
3. Kill Switch 优先级高于一切操作
4. 人类审批链不可被自动化绕过

---

## 依赖关系

- 依赖：Task 模型（RiskLevel）
- 被依赖：Pipeline 编排器、Agent 执行器、所有 API 层

---

## 相关文档

- [安全与审计 API](../../05-api/security.md)
- [干预系统设计](../../02-design/intervention.md)
- [系统架构](../../01-project/architecture.md)
