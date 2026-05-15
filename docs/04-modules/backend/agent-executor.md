# Agent 执行器模块

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

- **功能定位**：Agent 任务执行引擎，负责任务分配、执行调度和状态管理
- **所属层级**：backend
- **代码路径**：`backend/app/services/agent/agent_executor.py`

---

## 功能特性

- 任务分配（将任务绑定到 Agent）
- 执行调度（启动、暂停、恢复、取消）
- 全局暂停/恢复控制
- 执行状态追踪（IDLE → RUNNING → COMPLETED/FAILED/CANCELLED）
- 事件通知（通过 MessageBus 广播执行状态变化）

---

## 核心组件

### AgentExecutor

| 方法 | 说明 |
|------|------|
| `assign_task(task_id, agent_id, execute_fn)` | 分配任务给 Agent |
| `start_execution(task_id)` | 开始执行任务 |
| `execute_task_with_agent(task_id, agent_id)` | 使用指定 Agent 执行任务 |
| `pause_all()` | 全局暂停所有执行 |
| `resume_all()` | 全局恢复所有执行 |
| `cancel_execution(task_id)` | 取消任务执行 |
| `get_agent_current_task(agent_id)` | 获取 Agent 当前任务 |
| `get_running_tasks()` | 获取所有运行中的任务 |

### ExecutionStatus 枚举

| 状态 | 说明 |
|------|------|
| `IDLE` | 空闲 |
| `RUNNING` | 运行中 |
| `PAUSED` | 已暂停 |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |
| `CANCELLED` | 已取消 |

---

## 依赖关系

- 依赖：TaskBoard、MessageBus、SpeakingController、AgentService、LLMService
- 被依赖：PipelineOrchestrator、SecurityGuard、API 层

---

## 相关文档

- [Agent 服务](./agent-service.md)
- [任务看板](./task-board.md)
- [Pipeline 编排器](./pipeline-orchestrator.md)
