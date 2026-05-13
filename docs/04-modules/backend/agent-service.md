# Agent 服务模块

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：Agent 生命周期管理、模板管理和团队管理
- **所属层级**：backend
- **代码路径**：`backend/app/services/agent/`

---

## 功能特性

- Agent 模板管理（预设模板 + 自定义模板 + soul.md 加载）
- Agent 实例创建、查询、更新、删除
- 团队配置管理
- Soul 文件解析和集成

---

## 核心组件

### AgentService

Agent 管理的主要服务类。

#### 模板管理方法

| 方法 | 说明 |
|------|------|
| `get_all_templates()` | 获取所有模板 |
| `get_template(template_id)` | 获取指定模板 |
| `get_templates_by_type(agent_type)` | 按类型获取模板 |
| `get_templates_by_tag(tag)` | 按标签获取模板 |
| `create_custom_template(data)` | 创建自定义模板 |

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

### AgentType 枚举

```python
class AgentType(Enum):
    PM = "product_manager"           # 产品经理
    ARCHITECT = "architect"          # 架构师
    BACKEND = "backend_developer"    # 后端开发
    FRONTEND = "frontend_developer"  # 前端开发
    TESTER = "tester"                # 测试工程师
    DEVOPS = "devops"                # 运维工程师
    CUSTOM = "custom"                # 自定义
```

---

## 数据源优先级

1. **soul.md 文件**（优先）- 从 `agents/` 目录加载
2. **预设模板**（fallback）- 代码中定义的默认模板

---

## 依赖关系

- 依赖：LLM 服务、记忆服务、Soul 解析器
- 被依赖：任务管理、协作服务、API 层

---

## 相关文档

- [Agent 模型](./models/agent.md)
- [Agent 模型设计](../../02-design/agent-model.md)
- [Agent API](../../05-api/agents.md)