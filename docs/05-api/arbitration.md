# 冲突仲裁 API

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

多 Agent 结论冲突的仲裁 REST API，支持冲突检测、投票、启动仲裁和人工裁决。

**Base Path**: `/api/arbitration`

---

## 接口列表

### 检测冲突

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/arbitration/detect` |

```json
{
  "task_id": "task-xxx",
  "agent_results": [
    {"agent_id": "agent-1", "agent_name": "小张", "conclusion": "方案A", "reasoning": "..."},
    {"agent_id": "agent-2", "agent_name": "小王", "conclusion": "方案B", "reasoning": "..."}
  ]
}
```

### 列出仲裁议题

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/arbitration/issues?status=voting&task_id=xxx` |

### 获取议题详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/arbitration/issues/{issue_id}` |

### 启动仲裁

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/arbitration/issues/{issue_id}/start` |

### 投票

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/arbitration/issues/{issue_id}/vote` |

```json
{
  "agent_id": "agent-xxx",
  "vote": "agree",
  "reasoning": "方案A更符合需求"
}
```

`vote` 取值: `agree` / `disagree` / `abstain`

### 升级人工

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/arbitration/issues/{issue_id}/escalate` |

### 人工裁决

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/arbitration/issues/{issue_id}/resolve` |

```json
{
  "resolution": "采用方案A，但需要补充安全检查",
  "resolved_by": "admin"
}
```

---

## 相关文档

- [仲裁服务模块](../04-modules/backend/arbitration-service.md)
- [团队协作设计](../02-design/collaboration.md)
