# 卡死检测模块

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：基于心跳分析检测卡死的任务，自动通知用户
- **所属层级**：backend
- **代码路径**：`backend/app/services/execution/stuck_detector.py`

---

## 设计动机

Agent 执行 LLM 调用时可能因 API 超时、网络中断、模型无响应等原因陷入卡死状态。传统的断路器只检测错误率，卡死不产生 error 因此不会被触发。卡死检测器通过心跳机制独立监控每个运行中任务的存活状态，及时发现并通知卡死任务。

---

## 功能特性

- 后台异步监控循环（可配置间隔）
- 心跳超时检测（默认 120 秒无心跳视为卡死）
- 无心跳任务检测（从未发送心跳但已启动超过阈值）
- 自动通知（TaskBoard 评论 + MessageBus 系统告警）
- 优雅启停（`start_monitoring()` / `stop_monitoring()`）
- 仅检测运行中任务（paused/completed/failed 不受影响）

---

## 核心组件

### StuckDetector

| 方法 | 说明 |
|------|------|
| `start_monitoring()` | 启动后台监控循环 |
| `stop_monitoring()` | 优雅停止监控 |
| `check_stuck_tasks()` | 检查所有运行中任务的卡死状态，返回卡死列表 |
| `_handle_stuck_task(stuck)` | 处理卡死任务（评论 + 广播告警） |
| `_monitor_loop()` | 后台循环（每 `check_interval` 秒执行一次检查） |

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `heartbeat_threshold_seconds` | 120.0 | 心跳超时阈值（秒） |
| `check_interval_seconds` | 30.0 | 检查间隔（秒） |

---

## 检测逻辑

```
每 30 秒执行一次:
  now = datetime.now()
  threshold = 120 秒

  for each 运行中任务:
    if 从未发送心跳:
      if now - started_at > 120 秒:
        → 标记为卡死（reason: "no_heartbeat_ever"）
    else:
      if now - last_heartbeat > 120 秒:
        → 标记为卡死（reason: "heartbeat_timeout"）
```

### 卡死判定条件

| 条件 | 判定结果 | 原因 |
|------|----------|------|
| 心跳正常（< 120s） | 正常 | — |
| 心跳超时（> 120s） | 卡死 | `heartbeat_timeout` |
| 从未有心跳 + 启动超 120s | 卡死 | `no_heartbeat_ever` |
| 从未有心跳 + 启动不足 120s | 正常 | 刚启动，等待首心跳 |
| 状态非 running | 忽略 | 非运行中任务不检测 |

---

## 通知机制

检测到卡死任务时，`_handle_stuck_task()` 执行两项操作：

1. **TaskBoard 评论**：在卡死任务上添加系统评论，记录已流逝时间和 agent 信息
   ```
   [卡死检测] 任务已 180 秒无响应 (agent: dev-agent-1, 步骤: 3/5)
   ```

2. **MessageBus 广播**：向所有连接的客户端发送系统级别告警消息
   ```
   任务 task-xxx (agent: dev-agent-1) 疑似卡死 - 180秒无响应
   ```

前端通过轮询 `/api/execution/stuck` 端点（每 15 秒）获取卡死任务列表并显示警告。

---

## 生命周期

```
app lifespan startup:
  stuck_detector.start_monitoring(interval_seconds=30)
    → asyncio.create_task(_monitor_loop())

app lifespan shutdown:
  stuck_detector.stop_monitoring()
    → _running = False
    → monitor_task.cancel()
```

注意：为避免循环导入，`check_stuck_tasks()` 和 `_handle_stuck_task()` 使用懒加载导入（在方法体内部 `from app.services...`）。

---

## 依赖关系

- 依赖：AgentExecutor（获取运行中任务列表）、TaskBoard（添加评论）、MessageBus（广播告警）
- 被依赖：API 层（`/api/execution/stuck`）

---

## 相关文档

- [Agent 执行器](./agent-executor.md)
- [执行持久化](./execution-persistence.md)
- [检查点管理](./execution-checkpoint.md)
- [执行 API](../../05-api/execution.md)
- [干预系统设计](../../02-design/intervention.md)
