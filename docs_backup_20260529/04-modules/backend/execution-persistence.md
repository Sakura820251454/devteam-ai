# 执行持久化模块

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：任务执行状态和检查点的数据库持久化服务
- **所属层级**：backend
- **代码路径**：`backend/app/services/execution/task_persistence_service.py`
- **数据模型**：`backend/app/models/execution_db.py`

---

## 设计动机

Agent 执行恢复系统需要跨进程重启保持状态。原先 `TaskBoard`、`PipelineOrchestrator`、`AgentExecutor` 全部使用纯内存字典，进程重启后所有执行状态丢失。本模块将执行状态和检查点持久化到 SQLite，实现进程重启后状态恢复。

---

## 功能特性

- 任务执行状态的 upsert 持久化（idle → running → completed/failed）
- 步骤级检查点的保存和查询
- 心跳时间戳的原子更新
- 执行记录的清理
- 完全异步（SQLAlchemy async + async_sessionmaker）

---

## 核心组件

### TaskPersistenceService

| 方法 | 说明 |
|------|------|
| `initialize(session_maker)` | 注入 SQLAlchemy async session maker |
| `save_execution(task_id, agent_id, status, ...)` | 保存或更新任务执行状态 |
| `load_execution(task_id)` | 从数据库加载任务执行状态 |
| `save_checkpoint(task_id, step_index, ...)` | 保存步骤检查点 |
| `load_latest_checkpoint(task_id)` | 加载最新检查点（按 step_index DESC） |
| `list_checkpoints(task_id)` | 列出任务的所有检查点 |
| `update_heartbeat(task_id, step_index, total_steps)` | 更新心跳时间戳和步骤进度 |
| `delete_execution(task_id)` | 删除任务执行记录 |

### 数据模型

#### TaskExecutionModel

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID PK | 记录主键 |
| `task_id` | String(64) | 任务 ID（索引） |
| `agent_id` | String(64) | 执行 Agent ID |
| `status` | String(32) | 执行状态（idle/running/paused/completed/failed） |
| `current_step_index` | Integer | 当前步骤索引 |
| `total_steps` | Integer | 总步骤数 |
| `last_heartbeat_at` | DateTime | 最后心跳时间 |
| `heartbeat_count` | Integer | 心跳计数 |
| `accumulated_result` | Text | 累积的步骤结果 |
| `checkpoint_data` | JSON | 检查点数据快照 |
| `started_at` | DateTime | 开始时间 |
| `paused_at` | DateTime | 暂停时间 |
| `completed_at` | DateTime | 完成时间 |
| `updated_at` | DateTime | 最后更新时间 |

#### TaskCheckpointModel

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID PK | 检查点主键 |
| `task_id` | String(64) | 任务 ID（索引） |
| `step_index` | Integer | 步骤索引 |
| `step_name` | String(255) | 步骤名称 |
| `context` | JSON | 上下文快照（最近 10 条 LLM 消息） |
| `partial_result` | Text | 步骤 1~N 的累积结果 |
| `extra_data` | JSON | 附加元数据 |
| `created_at` | DateTime | 创建时间 |

---

## IO 模型

```
_execute_task_with_steps()
  ├─ task_persistence_service.save_execution()    ← 任务开始时
  ├─ for each step:
  │    ├─ task_persistence_service.save_checkpoint()  ← 每步完成后
  │    └─ task_persistence_service.update_heartbeat() ← 心跳更新
  └─ task_persistence_service.save_execution()    ← 任务结束时（status=completed/failed）
```

所有持久化调用采用 **fire-and-forget** 模式：DB 写入不阻塞主执行流程，写入失败仅记日志。

---

## 依赖关系

- 依赖：SQLAlchemy async_sessionmaker（通过 `initialize()` 注入）
- 被依赖：AgentExecutor、CheckpointManager、StuckDetector、API 层

---

## 相关文档

- [检查点管理](./execution-checkpoint.md)
- [卡死检测](./execution-stuck-detector.md)
- [Agent 执行器](./agent-executor.md)
- [执行 API](../../05-api/execution.md)
