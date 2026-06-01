# Pipeline 模板

**版本**: v1.1
**最后更新**: 2026-05-27

---

## 概述

- **功能定位**：定义 Pipeline 的阶段模板。Pipeline（WHAT）与协作策略（HOW）正交 —— Pipeline 决定任务分哪些阶段、每个阶段产出什么；协作策略决定 Agent 之间如何互动。用户选择模板后，在 **Stage Review 确认阶段**（v1.1 新增）可通过 AI 建议调整阶段，确认后锁定为最终阶段列表，Pipeline 按确认后的阶段驱动执行。
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/pipeline_templates.py`

---

## 核心组件

### StageDefinition

| 字段 | 说明 |
|------|------|
| `key` | 阶段唯一标识（如 "requirement"） |
| `label` | 阶段中文标签（如 "需求分析"） |
| `description` | 阶段描述 |
| `expected_artifact` | 预期产出物（文件名或目录） |
| `parallel_group` | 并行组名（同组可并行执行，null 表示串行） |

### PipelineTemplate

| 字段 | 说明 |
|------|------|
| `id` | 模板唯一标识 |
| `name` | 模板名称 |
| `description` | 模板用途描述 |
| `category` | 分类：simple / development / design / complex |
| `suggested_strategy` | 建议协作策略 |
| `stages` | 阶段定义列表 |

---

## 预定义模板（18 个）

### 简单任务（simple）

| ID | 名称 | 阶段 |
|----|------|------|
| `script_automation` | 脚本自动化 | 需求理解 → 脚本编写 → 运行验证 |
| `research_report` | 调研报告 | 问题拆解 → 信息检索 → 总结输出 |
| `bug_fix` | Bug 修复 | 问题复现 → 根因分析 → 代码修复 → 回归验证 |
| `documentation` | 文档编写 | 现状评估 → 内容编写 → 审核校对 |
| `env_setup` | 环境搭建 | 环境分析 → 配置实施 → 验证 |

### 开发任务（development）

| ID | 名称 | 阶段 |
|----|------|------|
| `web_application` | Web 应用 | 需求分析 → 架构设计 → 后端开发 ∥ 前端开发 → 集成测试 |
| `api_service` | API 服务 | 需求分析 → 接口设计 → 开发实现 → 测试 → 部署 |
| `data_pipeline` | 数据流水线 | 需求分析 → 数据建模 → ETL开发 → 质量验证 → 部署 |
| `cli_tool` | CLI 工具 | 需求分析 → 核心开发 → 测试 → 文档+发布 |
| `mobile_app` | 移动应用 | 需求分析 → 原型设计 → 前端开发 ∥ 后端开发 → 适配测试 |
| `browser_extension` | 浏览器插件 | 需求分析 → 功能开发 → 兼容测试 → 打包发布 |

### 设计任务（design）

| ID | 名称 | 阶段 |
|----|------|------|
| `tech_selection` | 技术选型 | 需求梳理 → 方案调研 → 对比分析 → 决策建议 |
| `architecture_design` | 架构设计 | 现状分析 → 方案设计 → 评审讨论 → 设计定稿 |
| `code_refactor` | 代码重构 | 代码分析 → 重构设计 → 风险评估 → 实施计划 |

### 复杂项目（complex）

| ID | 名称 | 阶段 |
|----|------|------|
| `saas_platform` | SaaS 平台 | 需求分析 → 系统架构 → 模块拆分 → 并行开发 → 集成测试 |
| `microservices` | 微服务系统 | 业务分析 → 服务拆分 → 并行开发 → 集成测试 → 容器化部署 |
| `ai_application` | AI 应用 | 场景分析 → 数据准备 → 模型开发 → 评估优化 → 集成部署 |
| `custom_template` | 自定义 | 空模板，由 LLM 在需求分析阶段生成 |

---

## LLM 动态调整

### 调整时机（v1.1 更新）

动态调整从"执行中调整"改为 **执行前的确认阶段**：

1. 用户在 `AgentConfigModal` 中选择模板并配置 Agent 团队
2. `StageReviewModal` 展示模板的阶段列表，用户可点击"AI 建议调整阶段"
3. `suggest_stage_adjustments()` 分析项目描述，返回调整建议
4. 用户可选择应用、修改或忽略 AI 的建议
5. 确认后调用 `confirm-stages` API，锁定阶段列表
6. Pipeline 启动后按确认的阶段驱动执行，不再中途修改

### suggest_stage_adjustments()

根据项目信息让 LLM 分析当前模板是否合适，返回调整建议：

- `add` — 新增阶段
- `remove` — 移除多余阶段
- `reorder` — 调整顺序
- `rename` — 改名

### apply_stage_adjustments()

应用 LLM 返回的调整结果，生成最终阶段列表。

---

## 依赖关系

- 依赖：PromptRegistry（`collaboration.pipeline_templates.*`）、LLMService
- 被依赖：PipelineOrchestrator、API 层（模板查询/调整接口）

---

## 相关文档

- [Pipeline 编排器](./pipeline-orchestrator.md)
- [策略推荐器](./strategy-recommender.md)
- [项目服务](./project-service.md)
