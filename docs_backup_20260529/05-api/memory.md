# Memory API

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

记忆管理接口，用于管理 Agent 的分层记忆系统，支持语义检索、记忆晋升、自动遗忘等高级功能。

---

## 接口列表

### 添加记忆

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories` |

#### 请求体

```json
{
  "agent_id": "agent-xxx",
  "content": "用户提到需要实现登录功能",
  "level": "working",
  "tags": ["conversation", "feature"],
  "session_id": "session-xxx"
}
```

**level 取值**: `working`, `short_term`, `long_term`

---

### 获取记忆详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/memories/{memory_id}` |

---

### 获取 Agent 记忆列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/memories/agent/{agent_id}` |

#### 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `level` | string | 按层级过滤 |
| `limit` | int | 限制数量（默认100） |
| `offset` | int | 偏移量 |

---

### 语义检索记忆

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/retrieve` |

#### 请求体

```json
{
  "agent_id": "agent-xxx",
  "search_query": "用户登录相关",
  "level": "long_term",
  "max_results": 10,
  "use_semantic": true
}
```

---

### 更新记忆

| 属性 | 值 |
|------|-----|
| **Method** | PUT |
| **Path** | `/memories/{memory_id}` |

#### 请求体

```json
{
  "content": "更新后的记忆内容",
  "tags": ["updated"],
  "relevance_score": 0.85
}
```

---

### 删除记忆

| 属性 | 值 |
|------|-----|
| **Method** | DELETE |
| **Path** | `/memories/{memory_id}` |

---

### 晋升记忆层级

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/promote/{memory_id}?to_level={level}` |

---

### 获取上下文提示词

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/memories/context/{agent_id}/prompt` |

---

### 创建/更新 Agent 上下文

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/context` |

#### 请求体

```json
{
  "agent_id": "agent-xxx",
  "role": "backend_developer",
  "system_prompt": "你是一个后端开发工程师...",
  "personality": {"type": "严谨型"}
}
```

---

### 获取记忆统计

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/memories/agent/{agent_id}/statistics` |

#### 响应

```json
{
  "working": 10,
  "short_term": 50,
  "long_term": 200,
  "total": 260
}
```

---

## 高级记忆管理 API

### 刷新记忆分数

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/agent/{agent_id}/refresh-scores` |

---

### 去重合并记忆

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/agent/{agent_id}/deduplicate` |

---

### 获取记忆质量评分

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/memories/quality/{memory_id}` |

---

### 获取敏感记忆

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/memories/agent/{agent_id}/sensitive` |

---

### 导出记忆数据

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/export` |

#### 请求体

```json
{
  "agent_id": "agent-xxx"
}
```

---

## 遗忘管理 API

### 获取遗忘计划

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/agent/{agent_id}/forget-plan` |

---

### 自动遗忘

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/agent/{agent_id}/auto-forget?dry_run=false` |

#### 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `dry_run` | bool | 仅返回计划不实际删除（默认 false） |

---

### 检查容量状态

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/agent/{agent_id}/capacity-check` |

---

## 上下文压缩 API

### 压缩上下文

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/memories/agent/{agent_id}/compress` |

#### 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `max_tokens` | int | 最大 token 数（默认 4096） |
| `strategy` | string | 压缩策略 |

**strategy 取值**: `auto`, `summary`, `importance`, `token_limit`, `merge_adjacent`, `truncate`

---

### 获取压缩后的提示词

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/memories/agent/{agent_id}/compressed-prompt?max_tokens=4096` |

---

## 相关文档

- [记忆服务模块](../04-modules/backend/memory-service.md)
- [记忆系统设计](../02-design/memory-system.md)