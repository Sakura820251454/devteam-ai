# 任务分析服务

**版本**: v1.0
**最后更新**: 2026-05-26

---

## 概述

- **功能定位**：Step 2 — 用 LLM 分析用户任务的领域、类型、复杂度，生成结构化分析结果供后续团队组建使用
- **所属层级**：backend
- **代码路径**：`backend/app/services/task/task_analyzer.py`

---

## 在团队组建流程中的位置

```
Step 1: 用户描述任务
Step 2: TaskAnalyzer.analyze()    ← 当前服务
Step 3: TeamSuggester.suggest()   → 基于分析结果建议角色+策略
Step 4: SoulMatcher.match()       → 将角色匹配到人格池
Step 5: 创建团队实例
```

---

## 核心组件

### TaskAnalysis

| 字段 | 类型 | 说明 |
|------|------|------|
| `domain` | str | 任务领域（信息查询/分析研究/文案写作/软件开发/数据分析/设计创意/其他） |
| `task_type` | str | 任务类型（探索研究型/执行交付型/决策分析型/创意产出型/混合型） |
| `sub_types` | List[str] | 子类型列表（混合型时包含 2+ 类型） |
| `complexity` | str | 复杂度（低/中/高） |
| `breakdown` | List[str] | 子领域拆解（2-5 个维度） |
| `key_challenge` | str | 关键挑战描述 |
| `analysis_summary` | str | 一句话分析摘要 |

### TaskAnalyzer

| 方法 | 说明 |
|------|------|
| `analyze(task_description)` | LLM 分析任务，返回 `TaskAnalysis` |
| `_parse_analysis(text)` | 从 LLM 响应中提取 JSON → 降级兜底 |

### 兜底策略

当 LLM 调用失败或 JSON 解析失败时，返回默认分析结果：
- domain: "其他领域"
- task_type: "探索研究型"
- complexity: "中"

---

## 依赖关系

- 依赖：LLMService（超时 45s + 外层 55s）、PromptRegistry（`task.analyze`, `task.analyze_system`）
- 被依赖：TeamSuggester

---

## 相关文档

- [团队建议服务](./team-suggester.md)
- [LLM 服务](./llm-service.md)
- [Prompt 架构](../../02-design/prompt-architecture.md)
