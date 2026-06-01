# 流水线产物与 Agent 协作策略澄清

## Status

Accepted

## Date

2026-05-21

## Context

在"四则运算"测试项目（计算 364 与 134 的加减乘除并保存结果到文件）运行后，对产物目录、日志、Agent 分配、流水线阶段等方面进行了审查。发现以下需要澄清的设计决策：

- `src/` 目录为空，所有产物堆在 `artifacts/coding/`
- `logs/project.log` 只有 1 行记录
- 3 个 Agent 中只有 1 个被分配了任务
- 产物文件命名使用 `_1_1` 到 `_1_8` 序号，迭代版本混乱
- 项目使用了 3 阶段自定义流水线而非标准 6 阶段

## 澄清结论

### 1. 任务驱动结构 — 灵活适配复杂度

**决策**: 不做固定的流水线阶段和产物结构。系统在任务分析阶段由 LLM 分析任务后，动态决定：
- 需要几个流水线阶段
- 每个阶段产出什么
- 最终项目目录结构

简单任务（如四则运算）用 3 阶段流水线即可，复杂任务（如 SaaS 平台）用完整 6 阶段。需求分析阶段的产出**必须**包含一份《项目结构方案》，明确定义目录布局和预期产物清单。

**依据**: 不同任务的结构差异巨大，强行套用固定模板会导致过度工程化或覆盖不足。

### 2. 产物目录 — 由分析阶段定义

**决策**: 不做 "必须放 `src/`" 的硬性规定。最终可执行代码、文档、配置文件的存放位置由需求分析阶段产出的《项目结构方案》决定。该方案可以是结构化 JSON（`project_structure.json`）或在分析报告中描述。

当前 workspace 的 `artifacts/` 目录定位为**中间产物**（阶段输出），最终交付物按结构方案放置。

### 3. 日志 — 详细记录每一步

**决策**: 流水线执行过程中必须详细持久化日志，包括：
- 每个阶段的启动和完成
- 每个 Agent 的发言和行动
- 每个文件的产出（路径、大小、任务来源）
- 任务状态变更
- 异常和重试

日志写入 workspace 的 `logs/project.log`。当前 pipeline orchestrator 仅在内存中调用 `pipeline.add_log()` 而未同步 `workspace_manager.add_log()`——这是一个需要修复的 bug。

### 4. 产物版本管理 — 只保留最终版

**决策**: 同一任务的多次迭代产物，最终只保留最终版本。中间迭代产物应在任务完成后自动清理。产物命名不使用 `_1_1` 这类无意义的序号，改用语义化命名。

**实现要点**:
- 每个任务的产物关联 `task_id`，任务完成后清理旧版本
- 产物命名直接使用模块名（如 `calculator.py`），不加迭代后缀

### 5. Agent 身份分配 — 人工选择 + 系统建议

**决策**: 保留当前 AgentPoolModal 的人工选择流程，但增加 LLM 驱动的智能建议：
- 系统分析任务后，推荐每个 Agent 应担任的角色
- 人可以在推荐基础上调整
- Agent 的最终身份在任务分析阶段确定，写入项目配置

**依据**: Agent 的角色不是固定的——同一个 Agent 在不同项目中可以担任不同角色。完全自动分配可能不符合用户意图，纯手动又缺少智能辅助。

### 6. 流水线阶段匹配 — 支持自定义模板

**决策**: 自定义流水线模板的阶段 key 不需要与标准 6 阶段一一对应。Pipeline orchestrator 应支持自定义模板的阶段流转，产物目录使用模板中定义的 stage key 而非硬编码的枚举值。

当前标准阶段枚举（`requirement_analysis`、`task_breakdown`、`task_execution`、`review`、`completed`）作为默认模板保留，但自定义模板的阶段不应被强制映射。

## Consequences

### 需要修改的代码

| 项 | 文件 | 改动 |
|---|---|---|
| 日志持久化 | `pipeline_orchestrator.py` | `pipeline.add_log()` 同步调用 `workspace_manager.add_log()` |
| 项目结构方案 | `pipeline_orchestrator.py` `_stage_requirement_analysis` | 需求分析输出中增加项目结构方案章节 |
| 产物清理 | `agent_executor.py` | 任务完成时清理同一 task_id 的旧版本产物 |
| 产物命名 | `agent_executor.py` | 去掉 `_{task_index}_{iteration}` 后缀，使用语义化文件名 |
| Agent 角色推荐 | `strategy_recommender.py` + `AgentPoolModal.tsx` | 增加角色智能推荐功能 |
| 自定义模板支持 | `pipeline_orchestrator.py` `_run_pipeline` | 根据模板动态构建阶段列表而非硬编码 5 阶段 |

### 不做改动的

- Agent 身份固定分配机制 — 保持动态
- 标准 6 阶段流水线 — 保留作为默认模板
- 人工选择 Agent 的交互流程 — 保持，增加推荐层

## 参考

- 测试项目 workspace: `D:\AIproject\devteam-workspaces\e784857c-4fb8-46ea-bddf-fe0245a017bb`
- 相关模块文档: [pipeline-orchestrator.md](/04-modules/backend/pipeline-orchestrator.md)
- 相关模块文档: [agent-executor.md](/04-modules/backend/agent-executor.md)
