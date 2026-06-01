# 团队建议服务

**版本**: v1.0
**最后更新**: 2026-05-26

---

## 概述

- **功能定位**：Step 3 + Step 4 — 基于任务分析结果和 Agent 人格池，由 LLM 建议团队角色+策略，再通过 SoulMatcher 将角色匹配到具体的 Agent 实例
- **所属层级**：backend
- **代码路径**：`backend/app/services/team/team_suggester.py`、`backend/app/services/team/soul_matcher.py`

---

## 核心组件

### TeamSuggester（team_suggester.py）

| 方法 | 说明 |
|------|------|
| `suggest(analysis: TaskAnalysis)` | LLM 分析 → 建议角色清单 + 协作策略 |
| `_parse_suggestion(text)` | 从 LLM JSON 响应解析 `TeamSuggestion` |

**输出数据结构**：

| 结构 | 关键字段 |
|------|---------|
| `SuggestedRole` | `role_name`, `responsibilities`, `required_capabilities`, `suggested_soul`, `priority` |
| `StrategySuggestion` | `recommended` (sequential/hierarchical/discussion), `reasoning`, `alternatives` |
| `TeamSuggestion` | `team_name`, `roles`, `strategy`, `overall_rationale` |

### SoulMatcher（soul_matcher.py）

三级匹配策略：

| 优先级 | 策略 | 置信度 |
|--------|------|--------|
| 1 | 精确匹配：`suggested_soul` 名称完全一致 | 0.9 |
| 2 | 模糊匹配：名称包含关系 | 0.7 |
| 3 | 兜底：选第一个未使用的 soul | 0.4 |

**方法**：

| 方法 | 说明 |
|------|------|
| `match_roles_to_souls(suggestion)` | 将建议的角色匹配到 soul 池中的 agent |
| `_find_best_match(role, soul_agents, used_souls)` | 三级匹配逻辑 |
| `create_team_instances(project_id, matches, strategy)` | 生成团队实例，绑定 agent 到项目 |

### 已用 soul 去重

每个 soul 只能匹配给一个角色。当所有 soul 都被占用时，后续角色给出警告。

---

## 协作策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| `sequential` | 顺序执行 | 1-2 人简单线性任务 |
| `hierarchical` | 层级委派 | 3+ 人复杂项目，coordinator 拆解后委派 |
| `discussion` | 圆桌讨论 | 多视角决策或创意场景 |

---

## 依赖关系

- 依赖：TaskAnalyzer（分析结果）、AgentTraitService（人格池文本）、AgentService（soul 查询/项目分配）、PromptRegistry
- 被依赖：API 层（团队组建接口）

---

## 相关文档

- [任务分析服务](./task-analyzer.md)
- [Agent 特质服务](./agent-trait-service.md)
- [Agent 服务](./agent-service.md)
