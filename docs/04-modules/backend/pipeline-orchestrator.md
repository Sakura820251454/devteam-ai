# Pipeline 编排器模块

**版本**: v2.0
**最后更新**: 2026-05-15

---

## 概述

- **功能定位**：项目 Pipeline 全生命周期编排，从需求分析到最终 Review
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/pipeline_orchestrator.py`

---

## 功能特性

- 五阶段 Pipeline（需求分析 → 任务拆解 → DAG 并行执行 → Review → 完成）
- LLM 驱动的需求分析和任务拆解
- DAG 拓扑排序并行执行（Kahn 算法）
- 安全守卫集成（风险检查 + 审批流程）
- 人工干预机制（暂停/恢复/停止/介入）
- 灵活发言协调（统筹 Agent 按需调控，不硬分阶段切换模式）
- 审计日志和断路器数据采集

---

## 核心组件

### PipelineOrchestrator

| 方法 | 说明 |
|------|------|
| `create_pipeline(project_id, name, agent_ids)` | 创建 Pipeline |
| `start_pipeline(pipeline_id)` | 启动 Pipeline（异步执行全部阶段） |
| `pause_pipeline(pipeline_id)` | 暂停 Pipeline |
| `resume_pipeline(pipeline_id)` | 恢复 Pipeline |
| `stop_pipeline(pipeline_id)` | 停止 Pipeline |
| `intervene(pipeline_id, message, agent_id)` | 人工介入（发送消息给 Agent） |
| `get_pipeline(pipeline_id)` | 获取 Pipeline 详情 |
| `get_active_pipeline()` | 获取当前活跃 Pipeline |
| `get_intervention_queue()` | 获取人工干预队列 |

### Pipeline 阶段

```
REQUIREMENT_ANALYSIS (20%)  → LLM 分析需求，识别风险和改进点
TASK_BREAKDOWN      (40%)  → LLM 拆解任务，按 JSON 格式输出
TASK_EXECUTION      (80%)  → DAG 拓扑排序 + 并行执行 + 安全守卫
REVIEW             (100%)  → LLM 审核所有完成任务给出改进建议
```

### PipelineStatus 枚举

| 状态 | 说明 |
|------|------|
| `IDLE` | 空闲 |
| `RUNNING` | 运行中 |
| `PAUSED` | 已暂停（人工） |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |

---

## 依赖关系

- 依赖：ProjectService、TaskBoard、AgentService、MessageBus、SpeakingController、AgentExecutor、SecurityGuard、AuditLogger、LLMService
- 被依赖：API 层

---

## 相关文档

- [项目管理服务](./project-service.md)
- [任务看板](./task-board.md)
- [安全服务](./security-service.md)
- [团队协作设计](../../02-design/collaboration.md)
