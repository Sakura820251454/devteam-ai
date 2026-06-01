# Tasks API

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

任务管理接口，用于创建、查询、更新和删除任务，支持任务看板视图和任务分配。

---

## 接口列表

### 获取任务列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/tasks` |

#### 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string | 按状态过滤 |
| `priority` | string | 按优先级过滤 |
| `assigned_agent` | string | 按分配的 Agent 过滤 |
| `tags` | string | 按标签过滤（逗号分隔） |
| `limit` | int | 限制数量（默认100） |
| `offset` | int | 偏移量 |

---

### 获取任务详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/tasks/{task_id}` |

---

### 创建任务

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/tasks` |

#### 请求体

```json
{
  "title": "实现用户登录功能",
  "description": "完成用户登录 API 的开发",
  "priority": "high",
  "assigned_agents": ["agent-xxx"],
  "tags": ["backend", "api"]
}
```

---

### 更新任务

| 属性 | 值 |
|------|-----|
| **Method** | PATCH |
| **Path** | `/api/tasks/{task_id}` |

---

### 删除任务

| 属性 | 值 |
|------|-----|
| **Method** | DELETE |
| **Path** | `/api/tasks/{task_id}` |

---

### 分配任务

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/tasks/{task_id}/assign` |

#### 请求体

```json
{
  "agent_ids": ["agent-xxx", "agent-yyy"]
}
```

---

### 更新任务状态

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/tasks/{task_id}/status` |

#### 请求体

```json
{
  "status": "in_progress",
  "changed_by": "system"
}
```

**status 取值**: `backlog`, `todo`, `in_progress`, `review`, `done`, `paused`, `cancelled`

---

### 添加评论

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/tasks/{task_id}/comment` |

#### 请求体

```json
{
  "comment": "这个任务需要更多信息",
  "author": "developer"
}
```

---

### 获取看板视图

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/tasks/board/all` |

#### 响应

```json
{
  "total": 25,
  "columns": {
    "backlog": [...],
    "todo": [...],
    "in_progress": [...],
    "review": [...],
    "done": [...]
  }
}
```

---

### 按状态获取任务

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/tasks/status/{status}` |

---

### 按 Agent 获取任务

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/tasks/agent/{agent_id}` |

---

### 搜索任务

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/tasks/search/{query}` |

---

### 获取任务数量

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/tasks/count/{status}` |

---

## 相关文档

- [任务模型设计](../02-design/task-model.md)
- [任务模型](../04-modules/backend/models/task.md)