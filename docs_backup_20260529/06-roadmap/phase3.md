# Phase 3: 干预系统

**版本**: v2.0  
**最后更新**: 2026-05-25

---

## 目标

实现人类干预机制。

---

## 功能列表

- [x] 紧急停止（Pipeline pause/resume/stop）
- [x] 任务调整（TaskBoard 卡片支持改优先级/状态/负责人，后端 API 联动）
- [x] Agent 替换（AgentTeamPanel 支持项目中替换 Agent，自动更新任务分配）
- [x] 手动接管（intervene API + MessageBus 人工消息注入）
- [x] 发布-订阅消息总线（阶段频道 + 任务频道 + 主题订阅）
- [x] 阶段产出物管理（artifact 写入 + 状态查询）
- [x] 可执行反馈（失败自动注入上下文重试）

---

## 相关文档

- [干预系统设计](../02-design/intervention.md)
