# Messages API

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

消息总线接口，用于管理 Agent 间的消息通信，支持广播、私聊、群组和任务消息。

---

## 接口列表

### 发送广播消息

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/messages/broadcast` |

#### 请求体

```json
{
  "sender_id": "agent-xxx",
  "sender_name": "小王",
  "content": "大家好，我是新来的后端开发",
  "message_type": "text",
  "metadata": {"channel": "welcome"}
}
```

**message_type 取值**: `text`, `system`, `task`, `notification`

---

### 发送私聊消息

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/messages/private` |

#### 请求体

```json
{
  "sender_id": "agent-xxx",
  "sender_name": "小王",
  "recipient_id": "agent-yyy",
  "content": "这个任务需要你的帮助",
  "message_type": "text"
}
```

---

### 发送群组消息

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/messages/group` |

#### 请求体

```json
{
  "sender_id": "agent-xxx",
  "sender_name": "小王",
  "group_id": "team-xxx",
  "recipients": ["agent-yyy", "agent-zzz"],
  "content": "团队会议即将开始",
  "message_type": "notification"
}
```

---

### 发送任务消息

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/messages/task/{task_id}` |

#### 请求体

```json
{
  "sender_id": "agent-xxx",
  "sender_name": "小王",
  "content": "任务进度更新",
  "message_type": "task"
}
```

---

### 获取消息历史

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/messages/history?channel={channel}&limit=100` |

---

### 获取 Agent 间对话

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/messages/conversation/{agent1_id}/{agent2_id}?limit=50` |

---

### 获取频道成员

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/messages/channel/{channel}/members` |

---

### 加入频道

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/messages/channel/{channel}/join?agent_id={agent_id}` |

---

### 离开频道

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/messages/channel/{channel}/leave?agent_id={agent_id}` |

---

## 相关文档

- [通信机制设计](../02-design/communication.md)