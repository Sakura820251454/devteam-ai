# Agent 上下文模块

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

- **功能定位**：Agent 的独立上下文管理，包含角色定义、对话历史、记忆条目和上下文窗口
- **所属层级**：backend
- **代码路径**：`backend/app/models/agent_context.py`

---

## 功能特性

- Agent 角色定义（role、system_prompt、personality）
- 对话历史（独立于会话的 Agent 视角对话记录）
- 记忆条目（Agent 级别的记忆管理）
- 上下文窗口控制（Token 限制）
- 任务状态追踪

---

## 核心模型

### AgentContext

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_id` | str | Agent ID |
| `session_id` | str | 会话 ID |
| `role` | str | Agent 角色 |
| `system_prompt` | str | 系统提示词 |
| `personality` | dict | 个性配置 |
| `status` | str | 当前状态 |
| `current_task` | str | 当前任务 ID |
| `task_progress` | float | 任务进度 (0.0-1.0) |
| `conversation_history` | List[dict] | 对话历史 |
| `memory_entries` | List[MemoryEntry] | 记忆条目 |
| `context_window` | List[str] | 上下文窗口 |
| `max_context_tokens` | int | 最大上下文 Token 数 |

### MemoryEntry

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | str | 记忆 ID |
| `content` | str | 记忆内容 |
| `level` | MemoryLevel | 记忆层级 (L1/L2/L3) |
| `tags` | List[str] | 标签 |
| `relevance_score` | float | 相关性分数 |

---

## 依赖关系

- 被依赖：AgentExecutor、PipelineOrchestrator

---

## 相关文档

- [记忆系统设计](../../02-design/memory-system.md)
- [记忆服务](./memory-service.md)
