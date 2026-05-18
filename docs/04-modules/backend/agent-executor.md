# Agent 执行器模块

**版本**: v2.0
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：Agent 任务执行引擎，负责任务分配、步骤化执行调度、取消控制和状态管理
- **所属层级**：backend
- **代码路径**：`backend/app/services/agent/agent_executor.py`

---

## v2.0 新增特性（执行恢复系统）

### 步骤化执行
任务不再是一次裸 LLM 调用，而是由 LLM 先规划 3-8 个子步骤，再逐步骤执行。每个步骤完成后保存检查点，支持从断点恢复。

### 可取消执行
- `asyncio.Event()` 作为取消令牌（cancellation token）
- `asyncio.Task` 句柄保存，支持 `.cancel()`
- 取消粒度在步骤边界：每步开始前检查取消信号
- `pause_execution()` 先 set 令牌再 cancel Task

### 超时保护
- LLM 调用传入超时参数（默认 120 秒/步）
- LLM Provider 层 `asyncio.timeout()` 包裹 HTTP 调用
- LLM Service 层 `asyncio.wait_for()` 双重保险

### 检查点与恢复
- 每步完成后自动保存检查点（上下文快照 + 累积结果）
- `resume_execution()` 加载最新检查点，从断点继续
- 恢复提示词明确告知 LLM"不要重复已完成的工作"

### 心跳机制
- 每步完成后发送心跳（更新 `last_heartbeat` 时间戳）
- 心跳数据供 StuckDetector 判断任务是否卡死

---

## 核心组件

### AgentExecutor

| 方法 | 说明 |
|------|------|
| `assign_task(task_id, agent_id, execute_fn)` | 分配任务给 Agent |
| `start_execution(task_id)` | 创建取消令牌和 asyncio.Task，开始执行 |
| `execute_task_with_agent(task_id, agent_id)` | 使用指定 Agent 执行任务（v2: 步骤化） |
| `_execute_task_with_steps(task, execution, cancellation_token)` | 步骤化执行核心逻辑 |
| `_plan_task_steps(task, agent)` | LLM 拆解任务为 3-8 个子步骤（JSON 格式） |
| `_parse_steps_from_response(response)` | 解析 LLM 返回的步骤（JSON → 编号列表降级） |
| `_build_step_prompt(step, task, accumulated, ...)` | 构建步骤级 prompt（含前几步结果） |
| `_fallback_single_execution(task, execution, ...)` | 降级方案：原单次 LLM 调用 |
| `_save_checkpoint(task_id, step_index, ...)` | 保存步骤检查点 |
| `_send_heartbeat(task_id, step_index, total_steps)` | 更新心跳时间戳 |
| `pause_execution(task_id)` | 设置取消令牌 + 取消 asyncio.Task |
| `resume_execution(task_id)` | 从数据库加载状态，从断点继续 |
| `cancel_execution(task_id)` | 取消任务（状态转换：IN_PROGRESS→BLOCKED→CANCELLED） |
| `pause_all()` | 全局暂停所有执行 |
| `resume_all()` | 全局恢复所有执行 |
| `get_execution_status(task_id)` | 获取含步骤进度、心跳的完整状态 |
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

### 执行状态结构

```python
{
    "task_id": str,
    "agent_id": str,
    "status": str,            # idle/running/paused/completed/failed/cancelled
    "started_at": datetime,
    "last_heartbeat": datetime,  # v2: 心跳时间戳
    "current_step": int,         # v2: 当前步骤索引
    "total_steps": int,          # v2: 总步骤数
    "accumulated_result": str,   # v2: 累积结果
    "execute_fn": callable,
    "cancellation_token": asyncio.Event,  # v2: 取消令牌
}
```

---

## 执行流程

```
start_execution(task_id)
  │
  ├─ 创建 asyncio.Event() cancellation_token
  ├─ 保存到 self._cancellation_tokens[task_id]
  ├─ asyncio.create_task(_execute_task(...))
  └─ 保存到 self._async_task_handles[task_id]
       │
       ▼
  _execute_task(task, cancellation_token)
    │
    ├─ [检查 DB] 是否有 checkpoint? → 是: 走恢复路径
    │                                   否: 走新执行路径
    ├─ [新执行] _execute_task_with_steps()
    │    ├─ _plan_task_steps() → JSON 步骤列表
    │    ├─ for each step:
    │    │    ├─ 检查 cancellation_token.is_set()
    │    │    ├─ 更新 current_step，报告进度
    │    │    ├─ _build_step_prompt()
    │    │    ├─ llm_service.chat(timeout=120s, cancellation_token=...)
    │    │    ├─ 累积结果
    │    │    ├─ _save_checkpoint()
    │    │    └─ _send_heartbeat()
    │    └─ 返回完整结果
    │
    ├─ [降级] _fallback_single_execution()
    │    └─ 当 _plan_task_steps() 解析失败时使用
    │
    └─ [异常] CancelledError → 保存 checkpoint → 标记 paused
```

---

## 取消机制详解

```
pause_execution(task_id)
  │
  ├─ cancellation_token.set()        ← 通知步骤边界停止
  ├─ async_task.cancel()             ← 取消 asyncio.Task
  │     └─ 触发 asyncio.CancelledError
  │           └─ finally: 保存 checkpoint 到 DB
  └─ 更新状态 → PAUSED

cancel_execution(task_id)
  │
  ├─ cancellation_token.set()
  ├─ async_task.cancel()
  ├─ 尝试 IN_PROGRESS → CANCELLED
  │     └─ 失败则 IN_PROGRESS → BLOCKED → CANCELLED
  └─ 清理句柄
```

---

## 依赖关系

- 依赖：TaskBoard、MessageBus、SpeakingController、AgentService、LLMService
- 依赖（v2 新增）：TaskPersistenceService、CheckpointManager
- 被依赖：PipelineOrchestrator、SecurityGuard、StuckDetector、API 层

---

## 相关文档

- [Agent 服务](./agent-service.md)
- [任务看板](./task-board.md)
- [Pipeline 编排器](./pipeline-orchestrator.md)
- [执行持久化](./execution-persistence.md)
- [检查点管理](./execution-checkpoint.md)
- [卡死检测](./execution-stuck-detector.md)
- [执行 API](../../05-api/execution.md)
