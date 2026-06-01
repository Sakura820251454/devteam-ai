# 任务分配卡片组件

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：任务分配卡片
- **代码路径**：`frontend/src/components/TaskAssignmentCard.tsx`

---

## 功能特性

- 显示任务信息
- 分配任务给 Agent
- 更新任务状态

---

## Props

| 属性 | 类型 | 说明 |
|------|------|------|
| `task` | Task | 任务数据 |
| `agents` | Agent[] | 可分配的 Agent |
| `onAssign` | function | 分配回调 |

---

## 相关文档

- [任务模型设计](../../02-design/task-model.md)
- [Task API](../../05-api/tasks.md)
