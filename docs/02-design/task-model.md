# 任务模型

**版本**: v2.0  
**日期**: 2026-05-13  
**状态**: 正式版  

---

## 1. 任务生命周期

```
创建任务 → 分配 Agent → 执行任务 → 任务完成
                           ↓
                        任务失败 → 重试/调整
```

---

## 2. 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 待分配 |
| `assigned` | 已分配给 Agent |
| `executing` | 执行中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `cancelled` | 已取消 |

---

## 3. 任务属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | string | 任务唯一标识 |
| `title` | string | 任务标题 |
| `description` | string | 任务描述 |
| `status` | enum | 任务状态 |
| `assigned_agent` | string | 分配的 Agent ID |
| `priority` | int | 优先级 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

---

## 4. 任务分配策略

### 自动分配

根据 Agent 的技能匹配度自动分配任务。

### 手动分配

用户手动指定 Agent 执行任务。

### 轮询分配

按顺序分配给可用的 Agent。

---

## 相关文档

- [Agent 模型](./agent-model.md)
- [任务看板](./task-board.md)
- [任务 API](../05-api/tasks.md)

---

**最后更新**: 2026-05-13  
**版本**: v2.0
