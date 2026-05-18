# Agent 人才库 & 项目组建弹窗

**版本**: v2.2
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：从人才库选择 Agent 组建项目团队，分配角色，启动项目
- **代码路径**：`frontend/src/components/AgentPoolModal.tsx`

---

## 功能特性

- 展示所有基于 soul.md 的 Agent（从 `/api/agents/soul-based` 加载）
- 左侧人才库选择 Agent，右侧分配临时职责（需求分析/架构设计/后端开发/前端开发/测试验证/代码评审/部署运维/文档编写）
- 填写项目名称和描述
- 点击"启动项目" → 创建项目 + 组建团队 + 启动 Pipeline

---

## 数据流

```
AgentPoolModal → onAgentsSelected(assignments, taskName, taskDesc, taskId)
  → AgentTeamPanel.handleAgentsSelected()
    → store.startProject(taskName, taskDesc, newAgents)
    → startSimulation(taskName, taskDesc)
```

---

## Props

| 属性 | 类型 | 说明 |
|------|------|------|
| `isOpen` | boolean | 是否显示 |
| `onClose` | () => void | 关闭回调 |
| `onAgentsSelected` | (agents: AgentAssignment[], taskName: string, taskDesc: string, taskId: string) => void | 项目创建回调 |
| `currentTask?` | Task | 可选：当前任务上下文 |

---

## 预定义职责

| ID | 标签 | 描述 |
|----|------|------|
| `requirement` | 需求分析 | 需求调研和功能规划 |
| `design` | 架构设计 | 系统架构和技术选型 |
| `backend` | 后端开发 | 后端服务实现 |
| `frontend` | 前端开发 | 用户界面实现 |
| `testing` | 测试验证 | 功能测试和质量保障 |
| `review` | 代码评审 | 代码审查和问题发现 |
| `deploy` | 部署运维 | 部署和运维监控 |
| `document` | 文档编写 | 技术文档编写 |

---

## 相关文档

- [Agent 服务模块](../backend/agent-service.md)
- [Agent 团队面板](./collaboration-view.md)

