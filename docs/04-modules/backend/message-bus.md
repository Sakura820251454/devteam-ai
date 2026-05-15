# 消息总线模块

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

- **功能定位**：Agent 间消息传递基础设施，支持广播、私聊、群组、任务频道
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/message_bus.py`

---

## 功能特性

- 多频道消息路由（公共/私有/任务/自定义频道）
- 发布-订阅模式（Agent 自由订阅频道）
- 三种消息类型（TEXT/ACTION/SYSTEM）
- 消息历史记录（按频道存储）
- 发送者过滤（订阅时可指定只接收特定发送者的消息）

---

## 核心组件

### MessageBus

| 方法 | 说明 |
|------|------|
| `subscribe(agent_id, channels, callback, filter_sender)` | 订阅频道 |
| `unsubscribe(subscription_id)` | 取消订阅 |
| `broadcast(message)` | 公共广播 |
| `send_private(message)` | 私聊（单接收者） |
| `send_group(message, group_id)` | 群组消息 |
| `send_to_task(message, task_id)` | 发送到任务频道 |
| `get_history(channel, limit, offset)` | 获取消息历史 |
| `get_conversation_between(agent1, agent2, limit)` | 获取两 Agent 间的对话 |
| `join_channel(agent_id, channel)` | 加入频道 |
| `leave_channel(agent_id, channel)` | 离开频道 |
| `clear_history(channel)` | 清除消息历史 |

### Message 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | str | 消息唯一 ID |
| `sender_id` | str | 发送者 ID |
| `sender_name` | str | 发送者名称 |
| `recipients` | List[str] | 接收者列表 |
| `channel` | str | 频道（public/private/task:xxx） |
| `content` | str | 消息内容 |
| `message_type` | MessageType | TEXT/ACTION/SYSTEM |
| `timestamp` | datetime | 时间戳 |

---

## 依赖关系

- 被依赖：所有协作服务（安全守卫、仲裁器、Pipeline 编排器、发言控制器）

---

## 相关文档

- [通信机制设计](../../02-design/communication.md)
