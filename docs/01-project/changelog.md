# 变更日志

**版本**: v2.2  
**最后更新**: 2026-05-18

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

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正
