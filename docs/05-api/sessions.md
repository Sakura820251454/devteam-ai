# Sessions API

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

会话管理接口，用于管理协作会话的创建、查询和状态控制。

---

## 接口列表

### 获取会话列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/sessions` |

#### 响应

```json
[
  {
    "id": "session-xxx",
    "title": "需求讨论会议",
    "status": "active",
    "participants": ["agent-xxx", "agent-yyy"],
    "message_count": 25,
    "token_used": 15000,
    "created_at": "2026-05-13T10:00:00Z"
  }
]
```

---

### 创建会话

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/sessions` |

#### 请求体

```json
{
  "title": "技术评审会议",
  "participant_ids": ["agent-xxx", "agent-yyy", "agent-zzz"]
}
```

---

### 获取会话详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/sessions/{session_id}` |

---

### 获取会话消息

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/sessions/{session_id}/messages` |

---

### 暂停会话

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/sessions/{session_id}/pause` |

---

### 恢复会话

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/sessions/{session_id}/resume` |

---

### 结束会话

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/sessions/{session_id}/end` |

---

## 状态枚举

| 状态 | 说明 |
|------|------|
| `active` | 活动中 |
| `paused` | 已暂停 |
| `ended` | 已结束 |

---

## 相关文档

- [会话模型](../04-modules/backend/models/session.md)