# 执行模型

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：任务执行状态和步骤检查点的 ORM 数据模型
- **所属层级**：backend
- **代码路径**：`backend/app/models/execution_db.py`

---

## 模型列表

### TaskExecutionModel

任务执行状态表 `task_executions`，记录每个任务的完整执行生命周期。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | UUID 主键 |
| `task_id` | String(64) | INDEX | 关联任务 ID |
| `agent_id` | String(64) | — | 执行 Agent ID |
| `status` | String(32) | — | 执行状态 |
| `current_step_index` | Integer | DEFAULT 0 | 当前步骤索引 |
| `total_steps` | Integer | DEFAULT 1 | 总步骤数 |
| `last_heartbeat_at` | DateTime | — | 最后心跳时间 |
| `heartbeat_count` | Integer | DEFAULT 0 | 心跳计数 |
| `accumulated_result` | Text | — | 累积的步骤结果 |
| `checkpoint_data` | JSON | DEFAULT {} | 检查点数据快照 |
| `started_at` | DateTime | — | 开始时间 |
| `paused_at` | DateTime | — | 暂停时间 |
| `completed_at` | DateTime | — | 完成时间 |
| `updated_at` | DateTime | — | 最后更新时间 |

### TaskCheckpointModel

任务检查点表 `task_checkpoints`，记录每个步骤完成后的检查点。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | UUID 主键 |
| `task_id` | String(64) | INDEX | 关联任务 ID |
| `step_index` | Integer | — | 步骤索引 |
| `step_name` | String(255) | — | 步骤名称 |
| `context` | JSON | DEFAULT {} | 上下文快照（最近 10 条 LLM 消息） |
| `partial_result` | Text | — | 步骤 1~N 的累积结果 |
| `extra_data` | JSON | DEFAULT {} | 附加元数据 |
| `created_at` | DateTime | — | 创建时间 |

> **注意**：`extra_data` 字段原命名为 `metadata`，因与 SQLAlchemy Declarative API 保留属性名冲突而改名。

---

## 状态流转

```
           save_execution()
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
  idle  →  running  →  completed
    │         │            │
    │         ├─ paused    ├─ failed
    │         │            │
    └─────────┴────────────┘
         delete_execution()
```

---

## 相关文档

- [执行持久化](../execution-persistence.md)
- [检查点管理](../execution-checkpoint.md)
- [卡死检测](../execution-stuck-detector.md)
- [Agent 执行器](../agent-executor.md)
