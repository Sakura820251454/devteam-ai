# 任务看板模块

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

- **功能定位**：任务全生命周期管理，支持状态流转、分配、搜索和事件通知
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/task_board.py`

---

## 功能特性

- 任务 CRUD（创建、查询、更新、删除）
- 状态流转控制（含合法转换校验）
- Agent 分配管理（多对多关系）
- 多维过滤查询（状态/优先级/Agent/标签/创建者）
- 看板视图（按状态分组）
- 事件通知机制（created/updated/status_changed/comment_added/deleted）

---

## 核心组件

### TaskBoard

| 方法 | 说明 |
|------|------|
| `create_task(title, description, priority, assigned_agents, ...)` | 创建任务 |
| `get_task(task_id)` | 获取任务 |
| `update_task(task_id, ...)` | 更新任务属性 |
| `assign_agents(task_id, agent_ids)` | 分配 Agent |
| `change_status(task_id, new_status, changed_by)` | 变更状态（含转换校验） |
| `add_comment(task_id, comment, author)` | 添加评论 |
| `delete_task(task_id)` | 删除任务 |
| `list_tasks(status, priority, agent, tags, ...)` | 多维过滤查询 |
| `get_tasks_by_status(status)` | 按状态获取 |
| `get_tasks_by_agent(agent_id)` | 按 Agent 获取 |
| `get_tasks_by_board()` | 看板视图（按状态分组） |
| `search_tasks(query)` | 文本搜索 |
| `register_handler(event, handler)` | 注册事件处理器 |
| `clear_all()` | 清空所有任务 |

---

## 依赖关系

- 依赖：Task 模型（TaskStatus, Priority）
- 被依赖：Pipeline 编排器、Agent 执行器、API 层

---

## 相关文档

- [任务模型设计](../../02-design/task-model.md)
- [任务模型](./models/task.md)
- [Task API](../../05-api/tasks.md)
