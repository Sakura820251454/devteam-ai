# API 文档

**版本**: v2.2  
**最后更新**: 2026-05-18

---

## 概述

本目录包含 DevTeam-AI 的 REST API 文档。

---

## API 列表

| API | 说明 |
|------|------|
| [Agents API](./agents.md) | Agent 管理接口 |
| [Tasks API](./tasks.md) | 任务管理接口 |
| [Memory API](./memory.md) | 记忆管理接口 |
| [Sessions API](./sessions.md) | 会话管理接口 |
| [Messages API](./messages.md) | 消息管理接口 |
| [Skills API](./skills.md) | 技能管理接口 |
| [Pipelines API](./pipelines.md) | 流水线管理接口 |
| [Projects API](./projects.md) | 项目管理接口 |
| [Workspaces API](./workspaces.md) | 工作区管理接口 |
| [Settings API](./settings.md) | 系统设置接口 |
| [Execution API](./execution.md) | 执行监控和恢复接口 (v2.3) |

---

## 基础 URL

```
http://localhost:8000/api
```

---

## 认证

API 使用 JWT Token 认证：

```
Authorization: Bearer <token>
```

---

## 响应格式

### 成功响应

```json
{
  "status": "success",
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "status": "error",
  "data": null,
  "message": "错误描述",
  "error_code": "ERR_001"
}
```

---

## 相关文档

- [API 开发规范](../03-development/api-guidelines.md)
- [模块文档](../04-modules/)
