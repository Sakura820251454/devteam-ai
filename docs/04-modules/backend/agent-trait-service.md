# Agent 特质服务

**版本**: v1.0
**最后更新**: 2026-05-26

---

## 概述

- **功能定位**：用 LLM 从 Agent 的 soul.md 定义中提取结构化能力画像，缓存复用，供任务匹配和团队组建使用
- **所属层级**：backend
- **代码路径**：`backend/app/services/agent/agent_trait_service.py`

---

## 核心组件

### AgentTraits

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_id` | str | Agent ID |
| `role_label` | str | 中文角色标签（如"数据分析师"、"后端开发"） |
| `skills` | List[str] | 具体技能列表 |
| `strength_areas` | List[str] | 擅长领域 |
| `collaboration_style` | str | 协作风格："分析型"/"务实型"/"主动型"/"严谨型" |
| `communication_style` | str | 沟通风格："简洁型"/"详细型" |
| `summary` | str | 一句话总结该 Agent 的特点和最擅长的任务类型 |

### AgentTraitService

| 方法 | 说明 |
|------|------|
| `get_trait(agent_id)` | 获取缓存的 traits（可能为 None） |
| `generate_trait(agent_id)` | LLM 分析 soul.md 生成 AgentTraits |
| `ensure_trait(agent_id)` | 懒加载：缓存命中返回，否则调用 generate |
| `ensure_traits_batch(agent_ids)` | 并行确保所有 agent 的 traits 已生成 |
| `build_soul_pool_text()` | 构建所有 agent 的 soul 池文本（供 TeamSuggester 使用） |

### 缓存机制

`_traits: Dict[str, AgentTraits]` — 内存缓存，首次调用 `generate_trait()` 后持久化到 agent 的 `growth.json` 文件，后续从文件加载。

---

## 数据来源

从 Agent 的 `soul.md` 文件解析：
- **Core Principles** → LLM 分析生成 `role_label`、`collaboration_style`
- **Execution Rules** → LLM 分析生成 `skills`、`strength_areas`
- 综合 → `summary`、`communication_style`

---

## 依赖关系

- 依赖：AgentService（读取 soul.md）、LLMService、PromptRegistry（`agent.trait.generate`, `agent.trait.generate_system`）
- 被依赖：TeamSuggester、StrategyRecommender、TaskBoard（trait 匹配任务分配）

---

## 相关文档

- [团队建议服务](./team-suggester.md)
- [Agent 服务](./agent-service.md)
- [任务看板](./task-board.md)
