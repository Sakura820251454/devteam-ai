# 变更日志

**版本**: v3.0.0  
**最后更新**: 2026-05-29

---

## [v3.0.0] - 2026-05-29

### 文档系统重构：AI 项目记忆

将 docs/ 从产品文档重构为 Claude Code 的**项目记忆**，确保文档与代码同步。

**核心变更**：
- 文档定位从"给人看的产品文档"改为"AI 项目记忆"
- 新增两类文档规范：结果文档（随代码更新）、过程文档（只增不改）
- 新增 `docs/process/` 目录存放过程文档（调研、决策、变更记录）
- 新增 `docs/08-tracker/` 目录追踪 doc-code 差异
- 新增 `CLAUDE.md` 文档同步硬性规则和自检清单

**P0 — 修复严重矛盾**：
- Pipeline 阶段：从"五阶段固定"改为"预设标准阶段 + LLM 可动态调整"
- 灰盒模型 → 白盒模型（内部细节用户都能掌控）
- 向量检索：Chroma → FAISS（与代码一致）
- 所有设计文档版本号统一为 v3.0

**P1 — 补充缺失文档**：
- 上下文压缩策略（6 种模式）
- Token 预算管理（TokenBudget 类）
- Pipeline 状态机（IDLE/RUNNING/PAUSED/COMPLETED/FAILED/CANCELLED）
- Coordinator 选举机制（run_coordinator_election）
- 记忆增强（衰减、去重、隐私）

**P2 — 标记未实现功能**：
- self-learning.md：模式发现 ❌、复盘流程 ⚠️、SKILL.md 路径 ⚠️（整体完成度约 30%）
- collaboration.md：Agent 间纠错建议 ❌
- memory-system.md：复盘手动触发记忆晋升 ❌

**P3 — 修复目录结构**：
- structure.md 更新为实际目录结构
- README.md 更新文档目录结构
- 根目录散落文件清理

**P4 — 清理重复内容**：
- 删除 PROJECT_COMPLETION_REPORT.md（过时报告）
- 删除 design-spec.md（内容与其他文档重复）
- 调研文档归档到 process/

---

## [v2.7] - 2026-05-19

### LLM 动态调整 Pipeline 阶段 (Phase 4)

**后端**：
- `suggest_stage_adjustments()` 函数：LLM 分析项目需求 → 建议增删改重排阶段
- `apply_stage_adjustments()` 函数：将 LLM 建议应用到模板
- API `POST /api/pipelines/templates/adjust` — 触发 LLM 阶段调整建议
- API `POST /api/pipelines/templates/apply` — 应用调整后的阶段列表

**前端**：
- `PipelineView` 新增 "AI 建议调整阶段" 按钮（需求分析阶段可见）
- LLM 返回后展示：分析说明 + 变更摘要（新增/移除/重排/重命名）+ 建议阶段流程图
- `api.ts` 新增 4 个 API 函数：`adjustPipelineTemplate`、`applyPipelineAdjustment`、`retryTaskWithFeedback`、`getArtifactStatus`

**核心理念**：Pipeline 不是写死的 — 用户选模板作为起点，LLM 根据项目实际需求建议优化，用户确认后生效。

---

## [v2.6] - 2026-05-19

### MetaGPT 三项增强 (Phase 3)

**MessageBus 增强发布-订阅**：
- 新增阶段频道：`stage:{project_id}:{stage_key}`，Agent 可按阶段订阅
- `send_to_stage()` 方法：发送到指定阶段
- `get_stage_context()` 方法：获取阶段完整上下文（阶段消息 + 公共消息）
- `get_prerequisite_context()` 方法：获取前置阶段所有消息（用于反馈）
- `subscribe_to_topics()` 方法：按消息主题标签订阅
- `cleanup_project_channels()` 方法：级联清理所有项目频道

**产出物管理**：
- `get_artifact_status()` 方法：查询各阶段产出物状态（有/无、文件列表）
- `get_prerequisite_artifacts()` 方法：获取前置阶段产出物内容（用于反馈）
- API `POST /api/workspaces/{id}/artifacts/status` — 产出物状态查询
- API `GET /api/workspaces/{id}/artifacts/prerequisites` — 前置产出物内容

**可执行反馈 (Executable Feedback)**：
- `_build_feedback_context()` 方法：收集项目阶段要求 + 前置产出物 + 历史消息 + 任务记录
- `execute_task_with_feedback()` 方法：首次执行失败后，自动注入反馈上下文重试一次
- API `POST /api/execution/tasks/{task_id}/retry-with-feedback` — 带反馈重试端点
- Agent 出错不瞎猜，基于共享上下文修正

**核心理念**：借鉴 MetaGPT 三项：
1. 阶段产出物（Artifact）→ 执行有目标、进度有感知
2. 发布-订阅消息 → Agent 只接收相关消息，不被无关内容淹没
3. 可执行反馈 → 出错时对照公共历史文档和消息，不瞎猜

---

## [v2.4] - 2026-05-19

### Agent 体系统一 (Phase 1)

统一项目创建流程中的 Agent 体系，从硬编码角色模板改为 soul.md 定义的 Agent 实例。

**AgentConfigModal 重写**：
- 删除 `PRESET_ROLES` 硬编码数组（6 个固定角色模板）
- 改为从 `/api/agents/soul-based` 加载 soul.md Agent（xiaoli、xiaochen 等 6 人）
- 新增协调策略选择（sequential/hierarchical/discussion/auto）
- hierarchical 模式下可指定统筹 Agent
- 保留 per-agent LLM 配置功能
- 后端不可用时 fallback 到与 soul.md 匹配的 MOCK 数据

**Home.tsx / store.ts 适配**：
- `handleAgentsConfigured` 简化 role 映射：soul agent 的 `type: custom` 映射为"团队成员"
- `startProject` 新增 `teamConfig` 参数，存储策略配置
- 通用型 agent 自动分配到所有 pipeline stage，角色在执行时动态协商
- `createWorkspace` API 签名扩展，支持传递 `teamConfig`

**协作系统设计文档**：
- 确立 Pipeline（WHAT）与协作策略（HOW）正交架构
- 定义 18 种 Pipeline 阶段模板（4 类：简单任务/开发项目/方案设计/复杂系统）
- 每个阶段关联明确产出物（借鉴 MetaGPT）
- 借鉴 MetaGPT 三项：发布-订阅消息、阶段产出物、可执行反馈

### Pipeline 模板系统 (Phase 2)

**后端**：
- 新增 `pipeline_templates.py`：定义 `PipelineTemplate` + `StageDefinition` 数据模型
- 18 种预定义模板覆盖 4 类任务（简单/开发/设计/复杂），每个阶段关联产出物
- API 端点 `GET /api/pipelines/templates` 和 `GET /api/pipelines/templates/{id}`，支持按类别筛选
- `workspace_manager` 支持动态 stage 目录创建 + 存储 `team_config` 和 `template`

**前端**：
- `CreateProjectModal` 增加模板选择（按类别分组 + 阶段预览 + 示例关联模板）
- `startProject` 接受 template 参数，用模板 stages 构建动态 pipeline
- `createWorkspace` API 传递 template 和 teamConfig 到后端

---

## [v2.3] - 2026-05-18

### Agent 执行恢复系统

解决 Agent 执行 LLM 调用时卡死无法中断、无法从断点恢复的痛点。

**步骤化执行**：
- LLM 先规划 3-8 个子步骤，再逐步骤执行（`_plan_task_steps()` / `_execute_task_with_steps()`）
- 步骤规划失败时降级为原单次 LLM 调用，向后兼容

**可取消执行**：
- `asyncio.Event()` 取消令牌 + `asyncio.Task.cancel()` 句柄保存
- 取消粒度在步骤边界：每步开始前检查取消信号
- `pause_execution()` 先 set 令牌再 cancel Task
- LLM Provider 层 `asyncio.timeout()` + Service 层 `asyncio.wait_for()` 双重超时保护

**检查点与断点恢复**：
- 每步完成后自动保存检查点（上下文快照 + 累积结果）
- `resume_execution()` 加载最新检查点，从断点继续
- 恢复提示词明确告知 LLM 不重复已完成工作
- 新建 `TaskExecutionModel` / `TaskCheckpointModel` ORM 模型

**卡死检测**：
- `StuckDetector` 后台心跳监控（120s 阈值 / 30s 检查间隔）
- 心跳超时或从未有心跳 → TaskBoard 评论 + MessageBus 系统告警
- 前端轮询 `/api/execution/stuck`，显示卡死警告

**新建模块**：
- `backend/app/models/execution_db.py` — ORM 模型
- `backend/app/services/execution/task_persistence_service.py` — 持久化服务
- `backend/app/services/execution/checkpoint_manager.py` — 检查点管理
- `backend/app/services/execution/stuck_detector.py` — 卡死检测
- `backend/app/api/execution.py` — 6 个执行管理 API 端点
- `frontend/src/components/ExecutionProgressPanel.tsx` — 步骤进度和卡死警告面板

**测试覆盖**：72 个新增测试（40 单元 + 32 集成），全部通过。

---

## [v2.2] - 2026-05-18

### soul.md 人才库 Bug 修复

- 修复 `agent_service.py` 中 `agents_dir` 路径解析 bug（少了一层 parent，导致找不到 `backend/agents/` 目录）
- `_load_from_soul_files()` 现在自动创建 Agent 实例到 `_agents`（之前只写 `_templates`），人才库 API 能正确返回 6 个 soul.md Agent
- 修复 `test_soul_parser.py` import 路径

### 项目创建流程统一

- `store.startProject` 新增 `customAgents` 参数，支持人才库选中的自定义 Agent
- Pipeline 阶段 `assignedAgents` 根据角色关键词自动分配
- `AgentPoolModal` 回调现在传递 `taskName` / `taskDesc`
- 人才库提交后调用 `startProject() + startSimulation()`，真正创建项目（之前只添加 Agent 到侧栏）

### 项目工作区管理系统

- 新建 `WorkspaceManager` 服务 — 创建物理项目目录（`devteam-workspaces/{project_id}/`）
- 目录结构：`project.json`, `docs/`, `src/`, `artifacts/{stage}/`, `logs/`
- 工作区独立于 DevTeam-AI 项目本身，通过 `config.workspace_root` 可配置
- 新建 `/api/workspaces` API — 创建、查询、管理项目工作区
- 前端 `store` 新增 `workspacePath` 状态，`PipelineView` 顶栏显示工作区路径
- `simulation.ts` 每个阶段完成时写入真实的 `.md` 产物文件到工作区

### 前端设置面板

- 新建 `/api/settings` API — 读写系统设置，持久化到 `data/settings.json`
- 新建 `SettingsModal` 组件 — 顶栏 ⚙ 按钮打开
- 用户可通过前端界面修改工作区存储路径，无需编辑配置文件

---

## [v2.1] - 2026-05-15

### 设计文档完善

- Agent 模型：明确人才库模式与灰盒模型设计
- 记忆系统：细化 L1/L2/L3 分层架构与 CrewAI 五操作模型
- 通信机制：确立灵活发言协调模式，不硬分阶段切换
- 干预系统：断路器改造为恢复性修复（上下文清理 + 记忆重载）

### 模块文档对齐设计

- 发言控制器：移除预设发言模式枚举，对齐灵活协调设计
- Agent 服务：移除预设角色枚举（AgentType），对齐人才库模式
- 安全服务：更新断路器描述为恢复性修复
- 记忆服务：语义检索标记为当前核心功能

### 其他更新

- 替换所有占位符 GitHub 链接为实际仓库地址

---

## [v2.0] - 2026-05-13

### 文档系统重构

- 统一文档系统为 VitePress
- 建立 7 个文档分类（01-07）
- 实现代码-文档一一对应
- 添加架构决策记录 (ADR) 框架

---

## [v1.0] - 2026-05-09

### 初始版本

- 项目初始化
- 基础架构设计
- MVP 功能开发

---

## 版本说明

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范，格式为 `vX.Y.Z`。

| 位置 | 名称 | 升级条件 | 示例 |
|------|------|---------|------|
| X | MAJOR | 删除/重命名 API、不兼容的数据库变更、架构重构 | v2.x.x → v3.0.0 |
| Y | MINOR | 新增 API、新增模块、新增功能 | v3.0.x → v3.1.0 |
| Z | PATCH | Bug 修复、文档更新、代码重构（不改行为） | v3.0.0 → v3.0.1 |

**注意**：v3.0.0 之前的版本使用 vX.Y 格式（2 位），v3.0.0 起统一为 vX.Y.Z（3 位）。
