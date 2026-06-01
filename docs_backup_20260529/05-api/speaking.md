# 发言控制 API

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

多 Agent 对话的发言顺序、Token 预算和速率限制管理接口。

**Base Path**: `/api/speaking`

---

## 接口列表

### 发言模式

#### 设置发言模式

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/mode` |

```json
{"session_id": "session-xxx", "mode": "round_robin"}
```

`mode` 取值: `sequential` / `round_robin` / `priority_based` / `free_style`

#### 获取发言模式

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/speaking/mode/{session_id}` |

---

### Token 预算

#### 设置预算

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/budget` |

```json
{"session_id": "session-xxx", "total_budget": 100000}
```

#### 获取预算

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/speaking/budget/{session_id}` |

#### 消耗 Token

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/consume?session_id=xxx&tokens=500` |

---

### 发言队列

#### 请求发言

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/request-speak` |

```json
{"session_id": "xxx", "agent_id": "agent-1", "agent_name": "小张", "priority": 5}
```

#### 下一个发言者

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/next/{session_id}` |

#### 跳过发言

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/skip/{session_id}/{turn_id}` |

#### 清空队列

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/clear/{session_id}` |

#### 查看队列

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/speaking/queue/{session_id}` |

---

### Agent 配置

#### 设置发言配置

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/agent-config` |

```json
{"agent_id": "xxx", "min_interval_seconds": 2.0, "max_messages_per_minute": 10}
```

#### 获取发言配置

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/speaking/agent-config/{agent_id}` |

---

### 会话控制

#### 获取会话状态

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/speaking/status/{session_id}` |

#### 强制停止发言

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/stop/{session_id}` |

#### 清理会话

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/speaking/cleanup/{session_id}` |

---

## 相关文档

- [发言控制器模块](../04-modules/backend/speaking-controller.md)
