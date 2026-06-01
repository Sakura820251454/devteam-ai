# Workspaces API

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

项目工作区管理接口，用于创建和管理物理项目目录。工作区独立于 DevTeam-AI 项目目录，默认存储在 `devteam-workspaces/`。

---

## 接口列表

### 创建工作区

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/workspaces` |

**Request Body:**
```json
{
  "project_id": "pipeline-1716000000000",
  "name": "项目名称",
  "description": "项目描述",
  "agents": [{"id": "pm", "name": "产品经理", "role": "产品经理"}],
  "stages": [{"key": "requirement_analysis", "label": "需求分析"}]
}
```

在磁盘上创建完整的项目目录结构（`project.json`, `docs/`, `src/`, `artifacts/{stage}/`, `logs/`）。

---

### 获取工作区列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/workspaces` |

返回所有已创建工作区的列表。

---

### 获取工作区详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/workspaces/{project_id}` |

返回 `project.json` 内容 + 文件目录树 + 工作区实际路径。

---

### 添加产物文件

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/workspaces/{project_id}/artifacts` |

**Request Body:**
```json
{
  "stage_key": "requirement_analysis",
  "name": "需求规格说明_v1.0.md",
  "content": "# 需求规格说明\n..."
}
```

将产物文件写入 `artifacts/{stage_key}/` 目录。

---

### 列出文件

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/workspaces/{project_id}/files?subdir=` |

返回指定子目录下的文件列表。

---

### 读取文件内容

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/workspaces/{project_id}/files/{file_path}` |

返回文件内容（UTF-8 文本）。

---

### 添加日志

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/workspaces/{project_id}/logs` |

**Request Body:**
```json
{
  "level": "info",
  "source": "pipeline",
  "message": "阶段完成: 需求分析"
}
```

追加日志行到 `logs/project.log`。

---

### 更新工作区状态

| 属性 | 值 |
|------|-----|
| **Method** | PATCH |
| **Path** | `/api/workspaces/{project_id}/status?status=completed&current_stage=delivery` |

---

### 删除工作区

| 属性 | 值 |
|------|-----|
| **Method** | DELETE |
| **Path** | `/api/workspaces/{project_id}` |

删除整个工作区目录。

---

## 工作区目录结构

```
devteam-workspaces/{project_id}/
├── project.json              # 项目元数据
├── docs/                     # 文档
├── src/                      # 源码
├── artifacts/                # 产物（按阶段分目录）
│   ├── requirement_analysis/
│   ├── task_breakdown/
│   ├── coding/
│   ├── review/
│   ├── testing/
│   └── delivery/
└── logs/
    └── project.log
```

---

## 相关文档

- [Settings API](./settings.md)
- [项目管理服务](../04-modules/backend/project-service.md)
