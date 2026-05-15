# 发言控制器模块

**版本**: v2.0
**最后更新**: 2026-05-15

---

## 概述

- **功能定位**：控制多 Agent 对话的发言顺序、速率和 Token 预算，不硬分模式，灵活适应不同任务场景
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/speaking_controller.py`

---

## 功能特性

- 灵活发言协调（不按阶段切换固定模式，由统筹 Agent 按需调控）
- Token 预算管理（会话级别的 Token 配额，80% 使用率警告）
- 发言速率限制（每分钟最大消息数，可配置最小发言间隔）
- 辩论轮次上限（同一议题自动上报用户裁决）
- 发言队列管理（加入、跳过、清空）
- 当前发言者追踪

---

## 核心组件

### SpeakingController

| 方法 | 说明 |
|------|------|
| `set_token_budget(session_id, total_budget)` | 设置 Token 预算 |
| `get_token_budget(session_id)` | 获取 Token 预算 |
| `consume_tokens(session_id, tokens)` | 消耗 Token |
| `request_speak(session_id, agent_id, agent_name, priority)` | 请求发言 |
| `next_turn(session_id)` | 获取下一个发言者 |
| `skip_turn(session_id, turn_id)` | 跳过当前发言 |
| `clear_queue(session_id)` | 清空发言队列 |
| `set_agent_config(agent_id, config)` | 设置 Agent 发言权限和限速参数 |
| `force_stop_speaking(session_id)` | 强制停止发言 |
| `cleanup_session(session_id)` | 清理会话相关资源 |

### TokenBudget

跟踪会话级别的 Token 配额使用情况：
- 总预算/已用量/剩余量
- 使用率与警告阈值（默认 80%）
- 耗尽检测

---

## 依赖关系

- 被依赖：Pipeline 编排器、Agent 执行器

---

## 相关文档

- [发言控制 API](../../05-api/speaking.md)
- [通信机制设计](../../02-design/communication.md)
