# 团队协作设计

**版本**: v3.1  
**日期**: 2026-05-27  
**状态**: Phase 1-4 已实现（v3.1 新增阶段确认门控和 Agent 主动提问机制）

---

## 1. 核心架构决策

**Pipeline（工作流结构，WHAT）与 协作策略（协调方式，HOW）是两个正交维度：**

- Pipeline = 任务分哪些阶段、每个阶段产出什么
- 协作策略 = Agent 之间如何互动、谁分配任务

同一个 Pipeline 可以用不同策略执行，两者不绑定。

---

## 2. 协作策略（4种 + 自动推荐）

| 策略 | 工作机制 | 适用场景 | 案例 |
|------|---------|---------|------|
| **sequential** | 1-2 Agent 按序执行，无分工 | 简单线性任务 | "写 CSV 导出脚本"、"查 BGP 协议原理并总结" |
| **hierarchical** | 统筹 Agent 拆解委派 → 工人执行 → 统筹 review 合并 | 复杂多模块项目 | "企业级 SaaS 平台"、"微服务系统重构" |
| **discussion** | 圆桌讨论 → 达成共识 → 按结论执行 | 技术决策/方案设计 | "MySQL vs PostgreSQL 选型"、"前后端分离方案设计" |
| **auto** | LLM 根据需求描述自动推荐 | 用户不确定时 | 需求分析阶段输出推荐策略 + 理由 |

### hierarchical 模式下的统筹 Agent

- 统筹 Agent 不是固定角色，是协作模式下分配给某个 Agent 的任务
- 从团队中选择一个 Agent 临时承担统筹职责
- 统筹 Agent 负责：任务拆解、分配、进度把控、成果集成
- 任务完成后回归普通 Agent 状态

---

## 3. Pipeline 阶段模板

用户选择模板后，LLM 在需求分析阶段可以调整（增加/删除/重排阶段/修改产出物），模板是起点而非终点。

### 📝 简单任务

| 模板 | 阶段与产出物 |
|------|------------|
| **script_automation** | 需求理解 → `需求摘要.md` → 脚本编写 → `脚本代码/` → 运行验证 → `验证结果.md` |
| **knowledge_research** | 问题拆解 → `问题分析.md` → 信息检索 → `调研笔记.md` → 总结输出 → `研究报告.md` |
| **bug_fix** | 问题复现 → `复现步骤.md` → 根因分析 → `根因分析.md` → 代码修复 → `修复代码/` → 回归验证 → `验证结果.md` |
| **doc_improvement** | 现状评估 → `评估记录.md` → 内容编写 → `文档/` → 审核校对 → `审核意见.md` |
| **config_setup** | 环境分析 → `环境说明.md` → 配置实施 → `配置文件/` → 验证 → `验证结果.md` |

### 🏗️ 开发项目

| 模板 | 阶段与产出物 |
|------|------------|
| **web_application** | 需求分析 → `需求文档.md` → 架构设计 → `技术方案.md` → 后端开发‖前端开发 → `后端代码/` + `前端代码/` → 集成测试 → `测试报告.md` → 部署 → `部署配置/` |
| **api_service** | 需求分析 → `需求文档.md` → 接口设计 → `API设计.md` → 开发实现 → `代码/` → 测试 → `测试报告.md` → 部署 → `部署配置/` |
| **data_pipeline** | 需求分析 → `需求文档.md` → 数据建模 → `数据模型.md` → ETL开发 → `ETL代码/` → 质量验证 → `验证报告.md` → 部署 → `部署配置/` |
| **cli_tool** | 需求分析 → `需求文档.md` → 核心开发 → `代码/` → 测试 → `测试报告.md` → 文档+发布 → `README.md` |
| **mobile_app** | 需求分析 → `需求文档.md` → 原型设计 → `原型/` → 前端开发‖后端开发 → `代码/` → 适配测试 → `测试报告.md` → 打包发布 |
| **browser_extension** | 需求分析 → `需求文档.md` → 功能开发 → `代码/` → 兼容测试 → `测试报告.md` → 打包发布 → `发布包/` |

### 🧭 方案设计

| 模板 | 阶段与产出物 |
|------|------------|
| **tech_evaluation** | 需求梳理 → `需求清单.md` → 方案调研 → `候选方案.md` → 对比分析 → `对比表.md` → 决策建议 → `推荐方案.md` |
| **architecture_design** | 现状分析 → `现状报告.md` → 方案设计 → `设计草案/` → 评审讨论 → `评审记录.md` → 设计定稿 → `架构设计.md` |
| **refactor_plan** | 代码分析 → `代码评估.md` → 重构设计 → `重构方案.md` → 风险评估 → `风险评估.md` → 实施计划 → `执行计划.md` |

### 🏢 复杂系统

| 模板 | 阶段与产出物 |
|------|------------|
| **saas_platform** | 需求分析 → `需求文档.md` → 系统架构 → `架构设计.md` → 模块拆分 → `模块清单.md` → 并行开发 → `各模块代码/` → 集成测试 → `测试报告.md` → 部署上线 → `运维手册.md` |
| **microservice_system** | 业务分析 → `领域分析.md` → 服务拆分 → `服务边界图.md` → 并行开发 → `各服务代码/` → 集成测试 → `测试报告.md` → 容器化部署 → `部署配置/` |
| **ai_application** | 场景分析 → `场景定义.md` → 数据准备 → `数据说明.md` → 模型开发 → `模型代码/` → 评估优化 → `评估报告.md` → 集成部署 → `部署配置/` |

---

## 4. 消息通信（发布-订阅）

基于 `MessageBus`（`services/collaboration/message_bus.py`），支持三种维度：

- **公共频道**：全员可见，用于讨论和决策公告
- **阶段频道**：按 Pipeline 阶段订阅，只接收当前阶段相关消息，避免无关信息淹没
- **任务频道**：`task:<task_id>` 格式，任务执行上下文专用

Agent 只订阅自己关心的消息，不受无关内容干扰。

---

## 5. 可执行反馈

Agent 执行出错时，系统自动提供：
- 当前阶段的产出物要求
- 前置阶段的产出物（需求文档、设计方案等）
- 相关历史消息摘要
- 其他 Agent 的纠错建议

不瞎猜，基于共享上下文修正。

> **⚠️ 实现状态**：前三项已实现（`_build_upstream_manifest` 方法）。"其他 Agent 的纠错建议"未实现。

---

## 6. 冲突仲裁

见 [Arbitrator 服务文档](../04-modules/backend/arbitration-service.md)。核心机制：
1. 检测冲突 → 创建仲裁议题
2. Agent 投票（AGREE/DISAGREE/ABSTAIN）
3. 多数同意 → 决议通过
4. 多数反对 → LLM 元 Agent 裁决
5. 平局 → 上报用户

---

## 7. Agent 主动提问机制（v3.1 新增）

Agent 在讨论或任务执行中发现以下情况时，主动暂停并向用户提问：

- 需求信息不完整（缺少公司背景、品牌色、目标用户等）
- Agent 之间无法达成共识（分歧无法解决）
- 缺少关键素材（Logo、文案、数据等）
- 多种方案各有优劣，需要用户决策

### 实现机制

1. **标记解析**：Agent 输出中使用 `[ASK_USER]`（任务执行中）或 `[NEEDS_CLARIFICATION]`（讨论中）标记
2. **状态转换**：相关任务自动转为 `WAITING_FOR_USER` 状态，Pipeline 暂停
3. **前端展示**：问题出现在干预队列（`question_for_user` 类型），通过 `AgentQuestions` 组件渲染
4. **用户答复**：通过 `POST /api/pipelines/{id}/respond-to-agent` API 答复，任务恢复执行

### 提示词注入

- 任务步骤提示词（`agent.executor.step_prompt.*`）：注入 `[ASK_USER]` 使用说明
- 讨论发言提示词（`collaboration.discussion.agent_speak`）：注入 `[NEEDS_CLARIFICATION]` 指令
- 需求合并提示词（`collaboration.pipeline.merge_analysis`）：注入"需要用户澄清"检测指令

详见 [Agent 执行器](../04-modules/backend/agent-executor.md) 和 [Pipeline 编排器](../04-modules/backend/pipeline-orchestrator.md)。

---

## 8. 阶段确认门控（v3.1 新增）

Pipeline 启动前，用户必须经过 **Stage Review** 确认阶段：

1. 用户选择模板并配置 Agent 团队
2. `StageReviewModal` 展示模板阶段，支持 AI 建议调整
3. 用户确认后调用 `confirm-stages` API（设置 `stages_confirmed` 标记）
4. `start_pipeline()` 检查确认标记后才允许启动

这确保了用户在 Pipeline 执行前有机会审核和调整阶段结构，而非执行中途被动干预。

---

## 9. Token 预算管理

SpeakingController 提供 token 使用量控制，防止单个会话消耗过多 token。

### 核心机制

- 每个会话设置 token 总预算（`total_budget`）
- 实时追踪已使用 token 数量
- 达到警告阈值（默认 80%）时发出警告
- 预算耗尽时阻止继续发言

代码位置：`backend/app/services/collaboration/speaking_controller.py`

---

## 10. Coordinator 选举机制

在 hierarchical 协作模式下，系统通过讨论选举 Coordinator（统筹者）。

### 选举流程

1. 各 Agent 自荐，说明自己适合统筹的理由
2. LLM 评估讨论记录，选出最佳 Coordinator
3. 选出的 Coordinator 负责任务拆解、分配、进度把控
4. 任务完成后回归普通 Agent 状态

代码位置：`backend/app/services/collaboration/discussion_orchestrator.py`

---

## 实现阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | Agent 体系统一：AgentConfigModal 改为 soul-based | ✅ 完成 |
| Phase 2 | 协作策略 + Pipeline 模板后端模型 | ✅ 完成 |
| Phase 3 | MetaGPT 三项增强（产出物、发布-订阅、反馈） | ✅ 完成 |
| Phase 4 | LLM 动态调整 Pipeline 阶段 | ✅ 完成 |
| Phase 5 | 阶段确认门控 + Agent 主动提问机制 | ✅ 完成 |

---

## 相关文档

- [Agent 模型](./agent-model.md)
- [通信机制](./communication.md)
- [任务模型](./task-model.md)
- [干预系统](./intervention.md)
- [Agent 配置弹窗](/04-modules/frontend/agent-config-modal.md)
- [Agent 执行器](/04-modules/backend/agent-executor.md)
- [Pipeline 编排器](/04-modules/backend/pipeline-orchestrator.md)

---

**最后更新**: 2026-05-27  
**版本**: v3.1
