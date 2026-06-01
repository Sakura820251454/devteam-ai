# 策略推荐器

**版本**: v1.0
**最后更新**: 2026-05-26

---

## 概述

- **功能定位**：用 LLM 根据项目需求、可用 Agent、Pipeline 模板等信息，推荐最适合的团队协作策略
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/strategy_recommender.py`

---

## 可选策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| `sequential` | 顺序执行，按阶段顺序一人负责一个阶段 | 1-2 人简单线性任务 |
| `hierarchical` | 层级委派，协调者拆解委派给成员独立执行，最后汇总 | 3+ 人复杂项目 |
| `discussion` | 圆桌讨论，Agent 集体讨论达成共识 | 多视角决策或创意场景 |

---

## 核心组件

### StrategyRecommendation

| 字段 | 类型 | 说明 |
|------|------|------|
| `recommended_strategy` | str | 推荐策略 |
| `confidence` | float | 置信度 (0.0-1.0) |
| `reasoning` | str | 推理说明 |
| `suggested_coordinator` | Optional[str] | 建议的协调者 agent_id（仅 hierarchical） |
| `alternative_strategies` | List[dict] | 备选策略 + 理由 |

### StrategyRecommender

| 方法 | 说明 |
|------|------|
| `recommend(project_name, project_description, requirements, agent_ids, template_id)` | LLM 推荐策略 |

### 推荐依据

LLM 综合以下因素做出推荐：
- 团队规模和成员特质覆盖
- 项目复杂度和任务类型
- 是否需要多专业视角或独立并行工作
- Pipeline 模板的建议策略（如有）

---

## 依赖关系

- 依赖：AgentService（agent 信息）、AgentTraitService（特质分析）、LLMService、PromptRegistry
- 被依赖：API 层（策略推荐接口）

---

## 相关文档

- [Pipeline 模板](./pipeline-templates.md)
- [团队建议服务](./team-suggester.md)
- [Agent 特质服务](./agent-trait-service.md)
