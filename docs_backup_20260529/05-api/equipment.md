# 装备系统 API

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

Agent 工具/装备管理接口，支持工具注册、查询、自动装备和卸载。

**Base Path**: `/equipment`

---

## 接口列表

### 工具管理

#### 获取工具列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/equipment/tools?tool_type=api&capability=code_generation` |

#### 获取工具详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/equipment/tools/{tool_id}` |

#### 注册工具

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/equipment/tools` |

```json
{
  "name": "code-reviewer",
  "type": "analysis",
  "version": "1.0",
  "description": "自动代码审查工具",
  "capabilities": ["code_review", "lint_check"],
  "suitable_tasks": ["code_review"],
  "tokens": 500, "memory_mb": 128, "seconds": 30
}
```

#### 注销工具

| 属性 | 值 |
|------|-----|
| **Method** | DELETE |
| **Path** | `/equipment/tools/{tool_id}` |

---

### Agent 装备

#### 分析任务并自动装备

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/equipment/agent/{agent_id}/equip?task_description=xxx` |

#### 分析任务需求

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/equipment/agent/{agent_id}/analyze?task_description=xxx` |

#### 获取 Agent 装备状态

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/equipment/agent/{agent_id}/equipment` |

#### 卸载工具

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/equipment/agent/{agent_id}/unequip/{tool_id}` |

#### 卸载所有工具

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/equipment/agent/{agent_id}/unequip-all` |

---

### 统计

#### 获取装备系统统计

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/equipment/stats` |

#### 更新工具使用统计

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/equipment/tools/{tool_id}/usage?agent_id=xxx&success=true&execution_time=1.5` |

---

## 相关文档

- [装备服务模块](../04-modules/backend/equipment-service.md)
