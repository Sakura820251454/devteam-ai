# Chat API

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

Agent 对话接口，支持普通对话和流式对话。

**Base Path**: `/api/chat`

---

## 接口列表

### 发送消息

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/chat` |

```json
{
  "agent_id": "agent-xxx",
  "session_id": "session-xxx",
  "message": "帮我分析这个需求"
}
```

**响应**:

```json
{
  "response": "好的，我来分析...",
  "agent_id": "agent-xxx",
  "session_id": "session-xxx"
}
```

### 流式对话

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/chat/stream` |

请求体同上。响应为 SSE（Server-Sent Events）流，每块数据以 `data: ` 开头，结束标记为 `data: [DONE]`。

---

## 相关文档

- [Agent 服务模块](../04-modules/backend/agent-service.md)
