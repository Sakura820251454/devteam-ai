# Agent 配置弹窗组件

**版本**: v3.0  
**最后更新**: 2026-05-19

---

## 概述

- **功能定位**：项目创建流程第二步，从 soul.md Agent 池中选择团队成员
- **代码路径**：`frontend/src/components/AgentConfigModal.tsx`

## v3.0 重大变更

从硬编码的 `PRESET_ROLES`（固定角色模板：产品经理、架构师...）改为从 `/api/agents/soul-based` 加载 soul.md 定义的 Agent 实例（xiaoli、xiaochen、xiaoliu、xiaozhang、xiaozhao、xiaowang）。

**核心理念变化**：
- 旧：选"角色"组建团队，Agent 有预设固定职业
- 新：选"人"组建团队，角色在执行过程中动态协商，soul.md 只定义行为准则

---

## 功能特性

### Agent 选择区
- 从后端 API `/api/agents/soul-based` 加载 soul-based Agent 列表
- 后端不可用时自动 fallback 到 `MOCK_SOUL_AGENTS`（6 个与 soul.md 匹配的 mock 数据）
- 每个 Agent 卡片展示：名称、类型标签、描述、核心能力
- 可展开查看 soul.md 中的核心原则 + 执行规则
- 支持按状态筛选（忙碌的 Agent 不可选）

### 协调策略选择
- **sequential**：顺序执行 — "写 CSV 导出脚本"
- **hierarchical**：层级委派 — "企业级 SaaS 平台"，需指定统筹 Agent
- **discussion**：圆桌讨论 — "技术选型评估"
- **auto**：LLM 智能推荐

### LLM 配置
- 保留 per-agent 自定义 LLM 配置
- 支持选择 provider/model/temperature/max_tokens
- 默认使用全局 LLM 配置

---

## Props

| 属性 | 类型 | 说明 |
|------|------|------|
| `isOpen` | boolean | 弹窗是否打开 |
| `onClose` | () => void | 关闭回调 |
| `onAgentsConfigured` | (agents: SoulAgent[], config: TeamConfig) => void | 确认回调 |

### SoulAgent 类型

```typescript
interface SoulAgent {
  id: string            // "soul_xiaoli"
  name: string          // "小莉"
  type: string          // "custom"（soul agent 均为通用型）
  description: string
  avatar_color: string
  capabilities: string[]
  status: string        // "idle" | "busy"
  is_active: boolean
  source: string        // "soul"
  soul_data?: {
    name: string
    core_principles: string[]
    execution_rules: string[]
  }
}
```

### TeamConfig 类型

```typescript
interface TeamConfig {
  strategy: 'sequential' | 'hierarchical' | 'discussion' | 'auto'
  coordinatorId?: string  // hierarchical 模式下必填
}
```

---

## 数据流

```
AgentConfigModal
  ├── fetch('/api/agents/soul-based') → SoulAgent[]
  ├── 用户选择 Agent + 策略
  └── handleConfirm()
        └── Home.handleAgentsConfigured(agents, teamConfig)
              ├── typeToRole 映射 → Agent[]
              └── store.startProject(name, desc, agents, teamConfig)
                    ├── allGeneric 检测 → stage 分配
                    ├── teamConfigs 存储
                    └── createWorkspace(pid, ..., teamConfig)
```

---

## 相关文档

- [协作系统设计](../../02-design/collaboration.md)
- [Agent 人才库弹窗](./agent-pool-modal.md)
- [Agent 模型](../../02-design/agent-model.md)
