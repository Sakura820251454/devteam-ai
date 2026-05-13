# Agents API

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

Agent 管理接口，用于创建、查询、更新和删除 Agent，以及管理 Agent 模板和团队。

---

## 接口列表

### 获取 Agent 列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/agents` |

#### 响应

```json
{
  "agents": [
    {
      "id": "agent-xxx",
      "name": "小张",
      "type": "backend_developer",
      "status": "idle",
      "template_id": "soul_xiaozhang"
    }
  ],
  "total": 5
}
```

---

### 获取 Agent 详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/agents/{agent_id}` |

---

### 创建 Agent（从模板）

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/agents` |

#### 请求体

```json
{
  "template_id": "pm_default",
  "name": "自定义产品经理"
}
```

---

### 创建 Agent（从 Soul 文件）

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/agents/from-soul` |

#### 请求体

```json
{
  "soul_name": "xiaowang",
  "name": "小王"
}
```

---

### 更新 Agent

| 属性 | 值 |
|------|-----|
| **Method** | PUT |
| **Path** | `/api/agents/{agent_id}` |

---

### 删除 Agent

| 属性 | 值 |
|------|-----|
| **Method** | DELETE |
| **Path** | `/api/agents/{agent_id}` |

---

### 获取所有模板

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/agents/templates` |

---

### 获取指定模板

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/agents/templates/{template_id}` |

---

### 按类型获取模板

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/agents/templates/type/{agent_type}` |

**agent_type 取值**: `product_manager`, `architect`, `backend_developer`, `frontend_developer`, `tester`, `devops`, `custom`

---

### 创建自定义模板

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/agents/templates` |

#### 请求体

```json
{
  "name": "我的定制Agent",
  "type": "custom",
  "description": "自定义Agent描述",
  "system_prompt": "你是一个定制的AI助手...",
  "capabilities": ["能力1", "能力2"],
  "tags": ["自定义", "测试"]
}
```

---

### 创建团队

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/api/agents/teams` |

#### 请求体

```json
{
  "name": "开发团队",
  "agent_ids": ["agent-xxx", "agent-yyy"]
}
```

---

### 获取团队列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/agents/teams` |

---

### 获取团队详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/agents/teams/{team_id}` |

---

## 相关文档

- [Agent 服务模块](../04-modules/backend/agent-service.md)
- [Agent 模型设计](../02-design/agent-model.md)