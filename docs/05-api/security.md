# 安全与审计 API

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

安全守卫和审计日志的 REST API，提供权限管理、Kill Switch 控制、断路器管理和审计日志查询。

**Base Path**: `/api/security`

---

## 接口列表

### 权限管理

#### 获取 Agent 权限列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/permissions/{agent_id}` |

#### 授予 Agent 权限

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/security/permissions/grant` |

```json
{
  "agent_id": "agent-xxx",
  "operations": ["query_data", "generate_code"]
}
```

#### 撤销 Agent 权限

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/security/permissions/revoke?agent_id=xxx&operation=generate_code` |

#### 设置默认权限

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/security/permissions/default/{agent_id}?agent_type=backend_developer` |

---

### 操作检查

#### 检查操作是否允许

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/check?operation=generate_code&agent_id=xxx` |

返回 `{allowed, requires_approval, risk_level, reason}`。

#### 获取所有风险级别

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/risk-levels` |

---

### Kill Switch

#### 全局紧急停止

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/security/emergency/stop` |

```json
{
  "triggered_by": "admin",
  "reason": "human_triggered",
  "message": "发现异常行为"
}
```

#### 解除紧急状态

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/security/emergency/reset` |

```json
{"triggered_by": "admin"}
```

#### 获取紧急状态

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/emergency/state` |

---

### 断路器

#### 获取 Agent 错误统计

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/circuit-breaker/{agent_id}` |

#### 重置断路器

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/security/circuit-breaker/{agent_id}/reset` |

---

### 审计日志

#### 查询审计日志

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/audit?action=emergency_stop&actor=admin&limit=100` |

#### 获取高危事件

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/audit/critical?limit=50` |

#### 获取审计摘要

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/audit/summary` |

#### 验证审计完整性

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/security/audit/verify` |

返回哈希链校验结果：`{valid, entries, errors}`。

---

## 相关文档

- [安全服务模块](../04-modules/backend/security-service.md)
