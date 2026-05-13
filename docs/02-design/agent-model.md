# Agent 人才库模式

**版本**: v2.0  
**日期**: 2026-05-13  
**状态**: 正式版  

---

## 1. 设计理念

传统的 Agent 系统通常采用「角色模板」模式——预定义好产品经理、架构师、开发等角色，然后从模板实例化。这种方式简单直接，但缺乏灵活性和个性化。

DevTeam-AI 采用「人才库」模式：每个 Agent 都是具有独特个性的个体，通过 `soul.md` 文件定义其行为准则和执行规则。这种方式更接近真实的人才管理，每个 Agent 都有自己独特的工作风格和思维方式。

---

## 2. soul.md 文件格式

每个 Agent 目录下包含 `soul.md` 文件，定义 Agent 的核心原则和执行规则：

```markdown
# Agent Soul

## Core Principles
- 解决实际问题，而不是描述解决方案
- 主动发现并解决问题，不等待指令

## Execution Rules
- 单步任务立即执行，不要只是计划
- 遇到不确定的问题，主动提问
```

---

## 3. Agent 生命周期

### 状态流转

```
空闲 (idle) → 已分配 (assigned) → 执行中 (executing) → 已完成 (completed)
                                    ↓
                                 失败 (failed) → 回归空闲
```

### 状态说明

| 状态 | 说明 |
|------|------|
| `idle` | 空闲状态，等待任务分配 |
| `assigned` | 已接受任务，等待执行 |
| `executing` | 正在执行分配的任务 |
| `completed` | 任务完成，回归空闲状态 |
| `failed` | 任务执行失败，回归空闲状态 |

---

## 4. 独立上下文设计

每个 Agent 拥有完全独立的上下文空间：

| 属性 | 说明 |
|------|------|
| `agent_id` | Agent 唯一标识符 |
| `conversation_history` | 独立的对话历史 |
| `memory_entries` | 三层记忆系统（L1/L2/L3） |
| `context_window` | 独立的上下文窗口 |
| `current_task` | 当前的临时职责 |
| `task_progress` | 任务进度追踪 |

---

## 5. 临时职责机制

Agent 的职责是**临时分配**的，任务完成后回归原始状态。这模拟了真实团队中员工接受项目任务的工作模式。

---

## 相关文档

- [记忆系统](./memory-system.md)
- [任务模型](./task-model.md)
- [Agent 服务模块](../04-modules/backend/agent-service.md)

---

**最后更新**: 2026-05-13  
**版本**: v2.0
