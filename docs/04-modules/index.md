# 模块文档

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

本目录包含代码模块的详细文档，每个文档与代码文件一一对应。

---

## 后端模块

| 模块 | 对应代码 | 说明 |
|------|----------|------|
| [Agent 服务](./backend/agent-service.md) | `services/agent/` | Agent 管理和执行 |
| [记忆服务](./backend/memory-service.md) | `services/memory/` | 分层记忆系统 |
| [LLM 服务](./backend/llm-service.md) | `services/llm/` | LLM 适配器 |
| [装备服务](./backend/equipment-service.md) | `services/equipment/` | Agent 装备管理 |
| [知识服务](./backend/knowledge-service.md) | `services/knowledge/` | 知识库管理 |
| [学习服务](./backend/learning-service.md) | `services/learning/` | 自我学习 |

### 数据模型

| 模型 | 对应代码 | 说明 |
|------|----------|------|
| [Agent 模型](./backend/models/agent.md) | `models/agent.py` | Agent 数据结构 |
| [记忆模型](./backend/models/memory.md) | `models/memory_db.py` | 记忆数据结构 |
| [任务模型](./backend/models/task.md) | `models/task.py` | 任务数据结构 |
| [会话模型](./backend/models/session.md) | `models/session.py` | 会话数据结构 |

---

## 前端模块

| 模块 | 对应代码 | 说明 |
|------|----------|------|
| [协作视图](./frontend/collaboration-view.md) | `CollaborationView.tsx` | Agent 协作界面 |
| [Agent 配置](./frontend/agent-config-modal.md) | `AgentConfigModal.tsx` | Agent 配置弹窗 |
| [Agent 池](./frontend/agent-pool-modal.md) | `AgentPoolModal.tsx` | Agent 池管理 |
| [流水线视图](./frontend/pipeline-view.md) | `PipelineView.tsx` | 任务流水线界面 |

---

## 相关文档

- [系统架构](../01-project/architecture.md)
- [API 文档](../05-api/)
