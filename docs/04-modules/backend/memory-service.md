# 记忆服务模块

**版本**: v2.0  
**最后更新**: 2026-05-15

---

## 概述

- **功能定位**：分层记忆系统实现，支持持久化存储、语义检索、记忆晋升、自动遗忘等功能
- **所属层级**：backend
- **代码路径**：`backend/app/services/memory/`

---

## 功能特性

- L1 工作记忆管理（当前会话）
- L2 短期记忆存储（最近会话摘要）
- L3 长期记忆存储（持久化知识）
- 语义检索支持（向量相似度 + 关键词混合检索）
- 记忆质量评估和晋升
- 自动遗忘机制
- 上下文压缩

---

## 核心组件

### PersistentMemoryManager

记忆管理的主要服务类，负责持久化存储和检索。

#### 基础操作方法

| 方法 | 说明 |
|------|------|
| `add_memory()` | 添加记忆 |
| `get_memory(memory_id)` | 获取记忆 |
| `get_agent_memories(agent_id)` | 获取 Agent 的所有记忆 |
| `update_memory(memory_id, ...)` | 更新记忆 |
| `delete_memory(memory_id)` | 删除记忆 |

#### 检索方法

| 方法 | 说明 |
|------|------|
| `retrieve_memory(agent_id, query)` | 检索相关记忆（支持语义检索） |
| `_semantic_retrieve()` | 语义检索 - 使用向量相似度 |
| `_keyword_retrieve()` | 关键词检索 |

#### 记忆层级管理

| 方法 | 说明 |
|------|------|
| `promote_memory(memory_id, to_level)` | 提升记忆到更高层级 |
| `_promote_if_needed(agent_id)` | 自动检查并晋升记忆 |

#### 上下文管理

| 方法 | 说明 |
|------|------|
| `create_or_update_context(agent_id, ...)` | 创建或更新 Agent 上下文 |
| `get_context_prompt(agent_id)` | 获取上下文提示词 |
| `get_compressed_context_prompt(agent_id)` | 获取压缩后的上下文提示词 |

#### 高级管理方法

| 方法 | 说明 |
|------|------|
| `refresh_memory_scores(agent_id)` | 刷新记忆分数并触发晋升 |
| `deduplicate_memories(agent_id)` | 去重并合并重复记忆 |
| `get_memory_quality(memory_id)` | 获取记忆质量评分 |
| `get_sensitive_memories(agent_id)` | 获取标记为敏感的记忆 |
| `auto_forget(agent_id, dry_run)` | 自动遗忘低质量或过期记忆 |
| `get_forget_plan(agent_id)` | 获取遗忘计划 |
| `check_capacity(agent_id)` | 检查记忆容量状态 |
| `compress_context(agent_id, max_tokens)` | 压缩 Agent 上下文 |

---

### VectorStore

向量存储和检索组件。

---

### 相关服务

| 服务 | 说明 |
|------|------|
| `promotion_service` | 记忆晋升服务 |
| `memory_enhancer` | 记忆增强服务（质量评估、去重） |
| `forget_service` | 遗忘服务 |
| `capacity_manager` | 容量管理服务 |
| `context_compressor` | 上下文压缩服务 |
| `semantic_retriever` | 语义检索服务 |

---

## 记忆层级

| 层级 | 值 | 说明 |
|------|-----|------|
| L1 | `working` | 工作记忆 - 当前会话 |
| L2 | `short_term` | 短期记忆 - 最近会话摘要 |
| L3 | `long_term` | 长期记忆 - 持久化知识 |

---

## 依赖关系

- 依赖：FAISS 向量库、SQLAlchemy、语义检索器
- 被依赖：Agent 服务、学习服务、API 层

---

## 相关文档

- [记忆模型](./models/memory.md)
- [记忆系统设计](../../02-design/memory-system.md)
- [Memory API](../../05-api/memory.md)