# 项目管理服务模块

**版本**: v2.2
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：项目全生命周期管理 + 物理工作区管理
- **所属层级**：backend
- **代码路径**：
  - `backend/app/services/collaboration/project_service.py` — 项目内存管理
  - `backend/app/services/project/workspace_manager.py` — 物理工作区管理

---

## 功能特性

- 项目 CRUD
- 阶段流转（预设标准阶段，LLM 可动态调整）
- 团队配置管理
- 任务拆解 Prompt 管理
- 物理工作区创建与管理（v2.2 新增）

---

## 核心组件

### ProjectService（内存管理）

`backend/app/services/collaboration/project_service.py`

| 方法 | 说明 |
|------|------|
| `create_project(name, description, requirements, ...)` | 创建项目 |
| `get_project(project_id)` | 获取项目 |
| `update_project(project_id, ...)` | 更新项目属性 |
| `list_projects(status)` | 列出项目 |
| `delete_project(project_id)` | 删除项目 |
| `advance_phase(project_id)` | 推进到下一阶段 |
| `set_task_breakdown_prompt(project_id, prompt)` | 设置任务拆解 Prompt |

### WorkspaceManager（物理工作区）

`backend/app/services/project/workspace_manager.py`

| 方法 | 说明 |
|------|------|
| `create_workspace(project_id, name, description, agents, stages)` | 在磁盘上创建项目目录结构 |
| `get_workspace(project_id)` | 读取 project.json + 文件树 |
| `list_workspaces()` | 列出所有工作区 |
| `add_artifact(project_id, stage_key, name, content)` | 写入产物文件 |
| `list_files(project_id, subdir)` | 列出目录文件 |
| `read_file(project_id, file_path)` | 读取文件内容 |
| `add_log(project_id, level, source, message)` | 追加运行日志 |
| `update_status(project_id, status)` | 更新项目状态 |
| `delete_workspace(project_id)` | 删除工作区目录 |

### 工作区目录结构

```
devteam-workspaces/{project_id}/
├── project.json              # 项目元数据（名称、状态、Agent、阶段）
├── docs/                     # 文档产出
├── src/                      # 源码产出
├── artifacts/                # 阶段产物
│   ├── requirement_analysis/
│   ├── task_breakdown/
│   ├── coding/
│   ├── review/
│   ├── testing/
│   └── delivery/
└── logs/
    └── project.log           # 运行日志
```

工作区默认存储在与 DevTeam-AI 平级的独立目录中（`../../devteam-workspaces`），可通过前端设置面板修改路径。配置持久化在 `data/settings.json`。

### ProjectStatus 枚举

| 状态 | 说明 |
|------|------|
| `PLANNING` | 规划中 |
| `IN_PROGRESS` | 进行中 |
| `PAUSED` | 已暂停 |
| `COMPLETED` | 已完成 |
| `CANCELLED` | 已取消 |

### ProjectPhase 枚举

项目支持预设阶段模板，LLM 可根据任务特点动态调整。标准阶段：

```
REQUIREMENT → DESIGN → DEVELOPMENT → TESTING → DEPLOYMENT
```

用户也可选择其他模板或让 LLM 自定义阶段。

---

## 依赖关系

- 被依赖：PipelineOrchestrator、API 层
- 依赖：`app.api.settings.get_workspace_root()` 读取配置

---

## 相关文档

- [Workspaces API](../../05-api/workspaces.md)
- [Settings API](../../05-api/settings.md)
- [Pipeline 编排器](./pipeline-orchestrator.md)
- [Projects API](../../05-api/projects.md)
