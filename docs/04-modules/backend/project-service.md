# 项目管理服务模块

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

- **功能定位**：项目全生命周期管理，包括创建、阶段流转和任务拆解
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/project_service.py`

---

## 功能特性

- 项目 CRUD
- 五阶段流转（需求 → 设计 → 开发 → 测试 → 部署）
- 团队配置管理
- 任务拆解 Prompt 管理

---

## 核心组件

### ProjectService

| 方法 | 说明 |
|------|------|
| `create_project(name, description, requirements, ...)` | 创建项目 |
| `get_project(project_id)` | 获取项目 |
| `update_project(project_id, ...)` | 更新项目属性 |
| `list_projects(status)` | 列出项目 |
| `delete_project(project_id)` | 删除项目 |
| `advance_phase(project_id)` | 推进到下一阶段 |
| `set_task_breakdown_prompt(project_id, prompt)` | 设置任务拆解 Prompt |

### ProjectStatus 枚举

| 状态 | 说明 |
|------|------|
| `PLANNING` | 规划中 |
| `IN_PROGRESS` | 进行中 |
| `PAUSED` | 已暂停 |
| `COMPLETED` | 已完成 |
| `CANCELLED` | 已取消 |

### ProjectPhase 枚举

```
REQUIREMENT → DESIGN → DEVELOPMENT → TESTING → DEPLOYMENT
```

---

## 依赖关系

- 被依赖：PipelineOrchestrator、API 层

---

## 相关文档

- [Pipeline 编排器](./pipeline-orchestrator.md)
- [Projects API](../../05-api/projects.md)
