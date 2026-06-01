# 任务模型

**版本**: v2.1
**最后更新**: 2026-05-27

---

## 概述

- **功能定位**：任务数据结构定义
- **代码路径**：`backend/app/models/task.py`

---

## 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 任务唯一标识 |
| `title` | string | 任务标题 |
| `description` | string | 任务描述 |
| `status` | enum | 任务状态 |
| `priority` | enum | 优先级 |
| `assigned_agents` | List[string] | 分配的 Agent ID 列表 |
| `collaborated_agents` | List[string] | 协作的 Agent ID 列表 |
| `dependencies` | List[string] | 依赖任务 ID 列表 |
| `linked_documents` | List[string] | 关联文档 ID 列表 |
| `created_by` | string | 创建者 |
| `tags` | List[string] | 标签列表 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `completed_at` | datetime | 完成时间（可选） |
| `history` | List[TaskHistory] | 历史记录 |

---

## 状态枚举

```python
class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    WAITING_FOR_USER = "waiting_for_user"  # v2.1: Agent 主动提问等待用户答复
```

---

## 优先级枚举

```python
class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
```

---

## 状态转换规则

| 当前状态 | 可转换到 |
|----------|----------|
| BACKLOG | TODO, CANCELLED |
| TODO | IN_PROGRESS, BACKLOG, CANCELLED |
| IN_PROGRESS | REVIEW, PAUSED, TODO, WAITING_FOR_USER |
| REVIEW | DONE, IN_PROGRESS |
| PAUSED | IN_PROGRESS, TODO |
| WAITING_FOR_USER | IN_PROGRESS, CANCELLED, BACKLOG |
| DONE | REVIEW |
| CANCELLED | BACKLOG |

### WAITING_FOR_USER 状态说明（v2.1 新增）

当 Agent 在任务执行中通过 `[ASK_USER]` 标记向用户提问时，任务自动转入此状态。Pipeline 暂停执行，等待用户通过 `respond-to-agent` API 答复。答复后任务恢复为 `IN_PROGRESS`。

---

## 相关文档

- [任务模型设计](../../../02-design/task-model.md)
- [Task API](../../../05-api/tasks.md)
