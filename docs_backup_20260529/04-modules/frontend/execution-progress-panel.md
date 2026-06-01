# 执行进度面板

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：实时展示任务执行的步骤级进度、心跳状态和卡死警告
- **所属层级**：frontend
- **代码路径**：`frontend/src/components/ExecutionProgressPanel.tsx`

---

## 功能特性

- 步骤进度条（颜色编码：绿色=运行中，橙色=暂停，红色=卡死）
- 心跳指示灯（绿色脉冲=正常，红色=卡死，显示已流逝时间）
- 卡死任务列表（实时轮询，每 15 秒更新）
- 可展开任务卡片（含重试/恢复按钮）
- 仅在 Pipeline 运行中时激活轮询

---

## 子组件

### StepProgressBar

步骤进度条组件，以视觉方式展示当前任务执行的步骤进度。

| 属性 | 类型 | 说明 |
|------|------|------|
| `currentStep` | number | 当前步骤索引 |
| `totalSteps` | number | 总步骤数 |
| `status` | string | 执行状态 |
| `stepNames` | string[] | 步骤名称列表 |

**颜色编码**：
- `running` → 绿色 `#22c55e`
- `paused` → 橙色 `#f97316`
- `stuck` / `failed` → 红色 `#ef4444`
- `completed` → 蓝色 `#3b82f6`

### HeartbeatIndicator

心跳状态指示灯，显示任务是否存活。

| 属性 | 类型 | 说明 |
|------|------|------|
| `lastHeartbeat` | string | 最后心跳时间（ISO 格式） |
| `isStale` | boolean | 心跳是否过期 |

**显示逻辑**：
- 心跳正常（< 120s）：绿色脉冲动画圆点 + "正常" + 已流逝秒数
- 心跳过期（> 120s）：红色静止圆点 + "STUCK" 标记 + 已流逝秒数
- 无心跳数据：灰色圆点 + "等待首次心跳..."

### MiniStuckList

紧凑的卡死任务列表，显示在进度面板顶部。

| 属性 | 类型 | 说明 |
|------|------|------|
| `stuckTasks` | StuckTaskInfo[] | 卡死任务数组 |

每项显示：task_id、agent_id、卡死原因、已流逝时间。

---

## 数据流

```
ExecutionProgressPanel
  │
  ├─ [组件挂载] → 启动 15 秒轮询
  │     └─ GET /api/execution/stuck
  │           → 更新 store.stuckTasks
  │
  ├─ [用户展开任务] → GET /api/execution/tasks/{id}/status
  │     └─ 显示 StepProgressBar + HeartbeatIndicator
  │
  ├─ [用户点击恢复] → POST /api/execution/tasks/{id}/retry?from_checkpoint=true
  │
  └─ [用户点击重试] → POST /api/execution/tasks/{id}/retry
```

---

## 集成点

| 父组件 | 集成方式 |
|------|----------|
| `PipelineView` | Pipeline 运行中时渲染进度面板 |
| `TaskBoard` | TaskCard 中集成迷你进度条 |
| `InterventionPanel` | 连接真实暂停/取消/重试 API |
| `AgentTeamPanel` | agent 有卡死任务时显示 "STUCK" 标记 |

---

## 依赖关系

- 依赖：`@/lib/api`（API 函数）、`@/lib/store`（Zustand 状态）
- 被依赖：PipelineView、TaskBoard、InterventionPanel、AgentTeamPanel

---

## 相关文档

- [流水线视图](./pipeline-view.md)
- [任务分配](./task-assignment.md)
- [执行 API](../../05-api/execution.md)
