# Pipelines API

**版本**: v3.0.0  
**最后更新**: 2026-05-29

---

## 概述

流水线管理接口，用于管理任务流水线的完整生命周期。

**代码路径**：`backend/app/api/pipelines.py`

---

## 接口列表

### 集合操作

#### 创建流水线

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines` |

**Request Body**：
```json
{
  "project_id": "string",
  "name": "string",
  "agent_ids": ["string"],
  "team_config": {}  // 可选
}
```

---

#### 获取流水线列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines` |
| **Query** | `project_id` (可选) |

---

#### 获取活跃流水线

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines/active` |
| **Query** | `project_id` (可选) |

---

#### 获取干预队列

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines/interventions/queue` |

---

### 模板管理

#### 获取模板列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines/templates` |
| **Query** | `category` (可选：simple/development/design/complex) |

---

#### 获取模板详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines/templates/{template_id}` |

---

#### LLM 阶段调整建议

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/templates/adjust` |

**Request Body**：
```json
{
  "project_name": "string",
  "project_description": "string",
  "template_id": "string"
}
```

---

#### 应用阶段调整

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/templates/apply` |

**Request Body**：
```json
{
  "template_id": "string",
  "adjustments": {}
}
```

---

### 策略推荐

#### 推荐协作策略

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/recommend-strategy` |

**Request Body**：
```json
{
  "project_name": "string",
  "project_description": "string",
  "requirements": "string",
  "agent_ids": ["string"],
  "template_id": "string"  // 可选
}
```

---

### 单个流水线操作

#### 获取流水线详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines/{pipeline_id}` |

---

#### 更新阶段配置

| 属性 | 值 |
|------|-----|
| **Method** | PUT |
| **Path** | `/api/pipelines/{pipeline_id}/stages` |

**Request Body**：
```json
{
  "stages": [{}],
  "project_id": "string"  // 可选
}
```

---

#### 确认阶段配置

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/confirm-stages` |

确认阶段配置并标记 pipeline 为可启动。必须在 start 之前调用。

**Request Body**：
```json
{
  "stages": [{}],
  "project_id": "string"  // 可选
}
```

---

#### 启动流水线

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/start` |

---

#### 暂停流水线

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/pause` |

---

#### 恢复流水线

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/resume` |

---

#### 停止流水线

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/stop` |

---

#### 关闭流水线

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/close` |

取消执行、保存状态为 PAUSED，用户可在之后恢复。

---

#### 从关闭状态恢复

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/resume-from-close` |

---

### 任务交互

#### 答复 Agent 提问

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/respond-to-agent` |

用户答复 Agent 的提问，恢复任务执行。

**Request Body**：
```json
{
  "task_id": "string",  // 可选
  "question_index": 0,
  "answer": "string"
}
```

---

#### 审批任务

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/approve-task` |

人工审批通过一个 REVIEW 状态的任务。

**Request Body**：
```json
{
  "task_id": "string"
}
```

---

### 人工干预

#### 发送干预消息

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/pipelines/{pipeline_id}/intervene` |

**Request Body**：
```json
{
  "message": "string",
  "agent_id": "string"  // 可选，不指定则广播
}
```

---

### 查询

#### 获取流水线日志

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines/{pipeline_id}/logs` |
| **Query** | `limit` (默认 50) |

---

#### 获取流水线任务

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines/{pipeline_id}/tasks` |

返回流水线的所有任务，含状态、分配、标签。

---

#### 获取流水线状态

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/pipelines/{pipeline_id}/status` |

返回流水线状态、当前阶段、进度、运行中任务、是否暂停。

---

## 相关文档

- [任务模型设计](../02-design/task-model.md)
- [团队协作设计](../02-design/collaboration.md)
- [Pipeline 编排器模块](../04-modules/backend/pipeline-orchestrator.md)
- [Pipeline 模板模块](../04-modules/backend/pipeline-templates.md)
