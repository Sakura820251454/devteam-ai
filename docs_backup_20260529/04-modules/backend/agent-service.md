# Agent 服务模块

**版本**: v2.2  
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：Agent 生命周期管理、人才库管理和团队管理
- **所属层级**：backend
- **代码路径**：`backend/app/services/agent/`

---

## 功能特性

- 人才库模式（无预设角色，任务驱动临时职责）
- Agent 实例创建、查询、更新、删除
- 团队配置管理
- Soul 文件解析和集成

---

## 核心组件

### AgentService

Agent 管理的主要服务类。

#### Soul 管理方法

| 方法 | 说明 |
|------|------|
| `load_soul(soul_name)` | 从 agents/ 目录加载 soul.md 文件 |
| `list_souls()` | 列出所有可用的 soul 配置 |

#### Agent 实例管理方法

| 方法 | 说明 |
|------|------|
| `create_agent(template_id, name)` | 从模板创建 Agent |
| `create_agent_from_soul(soul_name, name)` | 从 soul.md 创建 Agent |
| `get_soul_based_agents()` | 获取所有基于 soul 的 Agent |
| `create_agent_context(agent_id, session_id)` | 创建 Agent 上下文 |
| `get_agent(agent_id)` | 获取 Agent |
| `list_agents()` | 列出所有 Agent |
| `update_agent(agent_id, updates)` | 更新 Agent |
| `delete_agent(agent_id)` | 删除 Agent |

#### 团队管理方法

| 方法 | 说明 |
|------|------|
| `create_team(name, agent_ids)` | 创建团队 |
| `get_team(team_id)` | 获取团队 |
| `list_teams()` | 列出所有团队 |

---

### AgentExecutor

Agent 任务执行器（位于 `agent_executor.py`）。

---

## 数据源优先级

1. **soul.md 文件**（优先）- 从 `backend/agents/` 目录加载，定义 Agent 个性。启动时自动解析为模板并创建 Agent 实例，通过 `/api/agents/soul-based` 提供
2. **预设模板**（fallback）- 代码中定义的默认角色（产品经理、架构师等）

### soul.md 加载机制 (v2.2)

- `_load_from_soul_files()` 在 AgentService 初始化时执行
- 从 `backend/agents/agent_*/soul.md` 读取所有 Agent 定义
- 同时写入 `_templates`（模板表）和 `_agents`（实例表）
- Agent ID 格式：`soul_{name}`
- 自动推断 AgentType（基于名称关键词匹配）
- 路径基于 `Path(__file__).parent.parent.parent.parent / "agents"`（4 层 parent）

---

## 依赖关系

- 依赖：LLM 服务、记忆服务、Soul 解析器
- 被依赖：任务管理、协作服务、API 层

---

## 相关文档

- [Agent 模型](./models/agent.md)
- [Agent 模型设计](../../02-design/agent-model.md)
- [Agent API](../../05-api/agents.md)