# 检查点管理模块

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：任务执行检查点的保存、加载和恢复上下文构建
- **所属层级**：backend
- **代码路径**：`backend/app/services/execution/checkpoint_manager.py`

---

## 设计动机

原先 Agent 执行任务是一次裸 LLM 调用，没有中间状态保存。任务在第 3 步卡死后，resume 只能从头重新调用 LLM，丢失前 2 步的产出。检查点机制在每步完成后保存中间状态，使恢复时能从断点继续，避免重复工作。

---

## 功能特性

- 步骤级检查点自动保存（每步完成后触发）
- 上下文快照（最近 10 条 LLM 消息）保留对话连贯性
- 部分结果累积（避免恢复后重复已完成步骤的产出）
- 恢复提示词自动构建（告知 LLM 从检查点继续执行）
- 检查点列表查询（支持从指定检查点恢复）

---

## 核心组件

### CheckpointManager

| 方法 | 说明 |
|------|------|
| `save_checkpoint(task_id, step_index, step_name, messages_snapshot, partial_result, agent_state)` | 保存步骤检查点 |
| `load_checkpoint(task_id)` | 加载最新检查点 |
| `list_checkpoints(task_id)` | 列出所有检查点 |
| `build_resume_context(checkpoint)` | 构建恢复执行提示词 |

### 保存策略

- **触发时机**：每个步骤完成后立即保存
- **上下文窗口**：保留最近 10 条 LLM 消息作为快照
- **累积结果**：每个步骤完成后将产出追加到 `partial_result`
- **幂等性**：同一步骤多次保存会覆盖前一次（upsert 语义）

---

## 恢复提示词

`build_resume_context()` 构建的提示词结构：

```
你正在从检查点恢复执行。之前已完成了 N 个步骤：
- 步骤 1: [步骤名称] — 已完成
- 步骤 2: [步骤名称] — 已完成

已完成的累积结果：
[partial_result]

当前需要执行步骤 3: [步骤名称]
请从当前步骤继续，不要重复已完成的工作。
```

关键设计：明确告诉 LLM"不要重复已完成的工作"，防止恢复后 LLM 重新生成前几步的内容。

---

## IO 模型

```
AgentExecutor._execute_task_with_steps()
  │
  ├─ [步骤 1] → LLM 调用 → 结果累积
  │     └─ checkpoint_manager.save_checkpoint(task_id, step=1, ...)
  │
  ├─ [步骤 2] → LLM 调用 → 结果累积
  │     └─ checkpoint_manager.save_checkpoint(task_id, step=2, ...)
  │
  └─ [步骤 3] → ...卡死
        └─ 检查点已保留到 step=2

── 用户点击恢复 ──→

AgentExecutor.resume_execution(task_id)
  ├─ checkpoint_manager.load_checkpoint(task_id) → 获取 step=2 的检查点
  ├─ checkpoint_manager.build_resume_context(checkpoint) → 构建恢复提示词
  └─ _execute_task_with_steps(from_step=3) → 从步骤 3 继续
```

---

## 依赖关系

- 依赖：TaskPersistenceService
- 被依赖：AgentExecutor

---

## 相关文档

- [执行持久化](./execution-persistence.md)
- [卡死检测](./execution-stuck-detector.md)
- [Agent 执行器](./agent-executor.md)
