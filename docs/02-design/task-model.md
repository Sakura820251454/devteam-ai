# 任务模型与调度

**版本**: v3.0
**日期**: 2026-05-29
**状态**: 正式版  

---

## 1. 白盒模型

任务调度整体是一个白盒结构：

- **用户**：发布任务、验收最终结果
- **框架 + Agent**：自行完成计划生成、任务拆解、分配和执行
- **内部细节用户都能掌控**：用户可以随时查看内部执行细节

---

## 2. Pipeline 流水线

系统预设标准的 Pipeline 阶段，用户可直接使用预设阶段，也可让 LLM 根据任务特点调整后使用调整后的阶段。

### 标准阶段

```
需求分析 → 任务拆解 → DAG 并行执行 → Agent 互审 → 完成
```

| 阶段 | 说明 | 负责方 |
|------|------|--------|
| **需求分析** | LLM 分析需求完整性、可行性、风险、改进建议 | 框架自动 |
| **任务拆解** | LLM 将需求拆解为可执行子任务，输出 JSON | 框架自动 |
| **DAG 并行执行** | 拓扑排序，依赖满足的任务并行执行 | 框架 + 统筹 Agent |
| **Agent 互审** | 执行 Agent 互相评估任务完成情况 | 执行 Agent |
| **完成** | 用户验收最终结果 | 用户 |

### LLM 动态调整

用户选择模板后，LLM 在需求分析阶段可以：
- 增加/删除/重排阶段
- 修改产出物
- 模板是起点而非终点

阶段间不一定需要用文档来传递信息，只是当文档传递信息的效率高时，可以通过文档传递信息。

---

## 3. 任务状态

| 状态 | 说明 | 可转换至 |
|------|------|----------|
| `backlog` | 待排期 | todo, blocked, cancelled |
| `todo` | 待执行 | in_progress, blocked, backlog, cancelled |
| `blocked` | 等待依赖任务完成 | todo, in_progress, cancelled, waiting_for_user |
| `in_progress` | 执行中 | review, paused, blocked, cancelled, waiting_for_user |
| `waiting_for_user` | 等待用户确认 | in_progress, todo, cancelled |
| `review` | 待互审 | done, in_progress |
| `paused` | 已暂停 | in_progress, cancelled |
| `done` | 已完成 | review |
| `cancelled` | 已取消 | backlog |

---

## 4. 任务属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | string | 任务唯一标识 |
| `title` | string | 任务标题 |
| `description` | string | 任务描述 |
| `status` | enum | 任务状态（9 种） |
| `priority` | enum | 优先级（low/medium/high/urgent） |
| `risk_level` | enum | 风险等级（low/medium/high/critical） |
| `assigned_agents` | list | 分配的 Agent ID 列表 |
| `dependencies` | list | 依赖的前置任务 ID |
| `linked_documents` | list | 关联文档 |
| `tags` | list | 任务标签（角色、阶段等） |
| `created_by` | string | 创建者（user/pipeline/agent） |
| `approval_required` | bool | 是否需要人工审批 |

---

## 5. 任务分配

任务分配由**统筹 Agent** 根据当前情况决策，而非预定义的硬编码角色匹配：

- 统筹 Agent 评估任务需求和当前可用 Agent 的状态、能力、负载
- 根据实际情况决定谁最适合执行
- Agent 的职责是临时的，任务完成后回归空闲

---

## 6. 风险评级

采用**多维组合**评定风险等级：

| 维度 | 评价因素 |
|------|----------|
| **操作类型** | 读数据 / 写代码 / 删文件 / 改系统配置 / 改安全模块 |
| **影响范围** | 单文件 / 多模块 / 整个项目 |
| **可逆性** | git 可恢复 / 需手动恢复 / 不可逆 |

风险等级：

| 等级 | 说明 | 处理方式 |
|------|------|----------|
| `LOW` | 查询数据、生成文档 | 自动执行 |
| `MEDIUM` | 修改配置、生成代码 | Agent 自行评估 |
| `HIGH` | 删除数据、修改系统 Prompt、部署代码 | 需用户审批 |
| `CRITICAL` | 修改安全模块、删除审计日志 | 禁止执行 |

由 Agent 根据标准评估，高风险操作触发用户审批流程。

---

## 7. DAG 并行执行

任务拆解后生成依赖关系图，采用拓扑排序分层并行执行：

- 同一层级内无依赖关系的任务**并行执行**
- 依赖任务失败则**自动取消**下游任务
- 支持暂停/恢复单任务，不影响其他并行分支

---

## 8. 任务审核

任务完成后进入 REVIEW 状态，由**执行 Agent 互相评估**任务完成情况：

- 其他 Agent 检查代码质量、完成度、潜在风险
- 互审通过后进入 DONE 状态
- 用户只看最终呈现的结果

---

## 9. Pipeline 状态机

Pipeline 本身也有状态管理，用于控制整个流水线的生命周期。

### Pipeline 状态

| 状态 | 说明 |
|------|------|
| `IDLE` | 空闲，尚未启动 |
| `RUNNING` | 执行中 |
| `PAUSED` | 已暂停（用户干预或等待确认） |
| `COMPLETED` | 已完成 |
| `FAILED` | 执行失败 |
| `CANCELLED` | 已取消 |

### 状态转移

```
IDLE → RUNNING → COMPLETED
           ↓
         PAUSED → RUNNING
           ↓
         FAILED/CANCELLED
```

代码位置：`backend/app/services/collaboration/pipeline_orchestrator.py`

---

## 相关文档

- [Agent 模型](./agent-model.md)
- [团队协作](./collaboration.md)
- [干预系统](./intervention.md)
- [任务 API](../05-api/tasks.md)

---

**最后更新**: 2026-05-29
**版本**: v3.0
