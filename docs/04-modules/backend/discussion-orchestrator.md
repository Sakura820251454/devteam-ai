# 讨论编排器

**版本**: v1.0
**最后更新**: 2026-05-26

---

## 概述

- **功能定位**：多 Agent 真实对话引擎。每个 Agent 使用自己的 soul.md system prompt 参与讨论，每次发言都是独立的 LLM 调用，Agent 以其独特视角贡献。
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/discussion_orchestrator.py`

---

## 讨论模式

| 模式 | 枚举值 | 说明 | 状态 |
|------|--------|------|------|
| 轮流发言 | `ROUND_ROBIN` | 每人每轮发言一次 | 已实现 |
| 自由发言 | `FREE` | Agent 自主决定发言时机 | 保留 |
| 协调驱动 | `MODERATED` | 协调者决定下一个发言者 | 保留 |

---

## 核心组件

### DiscussionMessage

| 字段 | 说明 |
|------|------|
| `agent_id` | 发言者 ID |
| `agent_name` | 发言者名称 |
| `content` | 发言内容 |
| `round_number` | 所属轮次 |
| `timestamp` | 发言时间 |

### DiscussionOrchestrator

| 方法 | 说明 |
|------|------|
| `run_discussion(topic, participants, context, max_rounds)` | 启动多轮讨论 |
| `_agent_speak(agent_id, context, history, round, max_rounds)` | 单次 Agent 发言 |
| `_check_consensus(topic, positions)` | LLM 判断是否达成共识 |
| `_summarize_discussion(topic, history, has_consensus)` | 讨论摘要总结 |
| `_make_election_decision(project, agents, speakers)` | Coordinator 选举 |

### 讨论流程

```
run_discussion()
  │
  ├─ 第 1 轮: 每个 Agent 发表初步观点
  │    └─ _agent_speak(agent_id, topic="...", round=1)
  │
  ├─ 第 2~N 轮: 基于前面发言者的观点继续讨论
  │    ├─ 最后一轮: 附加强制表态指令
  │    └─ _agent_speak(agent_id, history="...", round=N)
  │
  ├─ _check_consensus() → LLM 判断共识
  │
  └─ _summarize_discussion() → 输出要点和结论
```

### Election 选举机制

用于 hierarchical 策略中选出 coordinator：
- 所有 Agent 参与短暂的选举讨论
- `_make_election_decision()` 评估领导力、项目管理能力、技术理解
- 选出一位最适合的 coordinator

---

## 依赖关系

- 依赖：AgentService（soul-based system prompt）、LLMService、PromptRegistry、MessageBus
- 被依赖：PipelineOrchestrator（需求分析阶段）、API 层

---

## 相关文档

- [消息总线](./message-bus.md)
- [Pipeline 编排器](./pipeline-orchestrator.md)
- [策略推荐器](./strategy-recommender.md)
