# Execution API

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

任务执行监控和管理接口，提供步骤级进度查询、卡死检测、检查点恢复等功能。

---

## 接口列表

### 1. 获取任务执行状态

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/execution/tasks/{task_id}/status` |
| **说明** | 获取任务的步骤级执行进度 |

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `agent_id` | string | 执行 Agent ID |
| `status` | string | 执行状态 |
| `current_step` | int | 当前步骤索引 |
| `total_steps` | int | 总步骤数 |
| `last_heartbeat` | datetime | 最后心跳时间 |
| `accumulated_result` | string | 累积结果 |
| `started_at` | datetime | 开始时间 |

---

### 2. 重试失败任务

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/execution/tasks/{task_id}/retry` |
| **Query** | `from_checkpoint=true` — 从最近检查点恢复 |
| **说明** | 重试失败或卡死的任务 |

**行为**：
- `from_checkpoint=false`（默认）：从头重新执行
- `from_checkpoint=true`：加载最近检查点，从上次中断的步骤继续

---

### 3. 获取卡死任务列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/execution/stuck` |
| **说明** | 列出所有疑似卡死的任务 |

**响应** (JSON 数组)：

```json
[
  {
    "task_id": "task-abc123",
    "agent_id": "dev-agent-1",
    "reason": "heartbeat_timeout",
    "elapsed_seconds": 185.3,
    "current_step": 3,
    "total_steps": 5
  }
]
```

---

### 4. 获取任务心跳

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/execution/heartbeat/{task_id}` |
| **说明** | 获取任务的心跳信息 |

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `last_heartbeat` | datetime | 最后心跳时间 |
| `heartbeat_count` | int | 心跳总数 |
| `current_step` | int | 当前步骤 |
| `total_steps` | int | 总步骤数 |
| `is_stale` | bool | 心跳是否过期（> 120s） |

---

### 5. 列出任务检查点

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/execution/tasks/{task_id}/checkpoints` |
| **说明** | 列出任务的所有检查点 |

**响应** (JSON 数组，按 step_index 升序)：

```json
[
  {
    "id": "cp-uuid-1",
    "task_id": "task-abc123",
    "step_index": 1,
    "step_name": "需求分析",
    "partial_result": "...",
    "metadata": {},
    "created_at": "2026-05-18T10:30:00"
  }
]
```

---

### 6. 从检查点恢复

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/execution/tasks/{task_id}/checkpoints/{checkpoint_id}/restore` |
| **说明** | 从指定的检查点恢复任务执行 |

此端点允许用户选择特定的检查点（而非仅最新检查点）恢复任务，适用于需要跳过某个有问题的步骤、回退到更早检查点的场景。

---

## 错误码

| 错误码 | 说明 |
|------|------|
| `ERR_NOT_FOUND` | 任务或检查点不存在 |
| `ERR_INVALID_STATE` | 任务状态不允许此操作（如正在运行的任务不能恢复） |
| `ERR_AGENT_BUSY` | Agent 正忙于其他任务 |

---

## 相关文档

- [执行持久化](../04-modules/backend/execution-persistence.md)
- [检查点管理](../04-modules/backend/execution-checkpoint.md)
- [卡死检测](../04-modules/backend/execution-stuck-detector.md)
- [Agent 执行器](../04-modules/backend/agent-executor.md)
