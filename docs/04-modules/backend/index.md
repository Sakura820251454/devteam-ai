# 后端模块文档

**最后更新**: 2026-05-14

---

## 概述

本目录包含后端服务模块的详细文档。

---

## 服务模块

| 服务 | 说明 |
|------|------|
| [Agent 服务](./agent-service.md) | Agent 生命周期管理 |
| [Agent 执行器](./agent-executor.md) | Agent 任务执行引擎 |
| [消息总线](./message-bus.md) | Agent 间消息传递 |
| [发言控制器](./speaking-controller.md) | 发言顺序和速率控制 |
| [任务看板](./task-board.md) | 任务全生命周期管理 |
| [Pipeline 编排器](./pipeline-orchestrator.md) | 项目 Pipeline 编排 |
| [项目管理](./project-service.md) | 项目生命周期管理 |
| [仲裁服务](./arbitration-service.md) | 多 Agent 冲突仲裁 |
| [安全服务](./security-service.md) | 安全守卫 + 审计日志 |
| [记忆服务](./memory-service.md) | 分层记忆系统 |
| [LLM 服务](./llm-service.md) | LLM 适配和调用 |
| [装备服务](./equipment-service.md) | Agent 装备管理 |
| [知识服务](./knowledge-service.md) | 知识库管理 |
| [学习服务](./learning-service.md) | 自我学习机制 |
| [共享服务](./shared-services.md) | Soul 解析、批处理与重试 |

## 数据模型

| 模型 | 说明 |
|------|------|
| [Agent 模型](./models/agent.md) | Agent 数据结构 |
| [Agent 上下文](./agent-context.md) | Agent 独立上下文 |
| [记忆模型](./models/memory.md) | 记忆数据结构 |
| [任务模型](./models/task.md) | 任务数据结构 |
| [会话模型](./models/session.md) | 会话数据结构 |
| [Gear 模型](./models/gear.md) | 装备数据结构 |

---

## 相关文档

- [项目结构](../../03-development/structure.md)
- [API 文档](../../05-api/)
