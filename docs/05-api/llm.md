# LLM API

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

LLM 调用、模型管理、成本追踪和 Token 统计的 REST API。

**Base Path**: `/llm`

---

## 接口列表

### 模型管理

#### 获取可用模型列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/models` |

#### 获取模型详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/models/{model_name}` |

#### 获取可用 Provider 列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/providers` |

---

### 对话

#### 发送对话请求

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/llm/chat` |

```json
{
  "messages": [{"role": "user", "content": "Hello"}],
  "agent_id": "agent-xxx",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "track_cost": true
}
```

---

### 成本追踪

#### 获取成本摘要

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/costs/summary?agent_id=xxx&task_id=xxx` |

#### 获取成本记录

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/costs/records?limit=100` |

#### 清除成本记录

| 属性 | 值 |
|------|-----|
| **Method** | DELETE |
| **Path** | `/llm/costs/records` |

#### 实时成本

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/costs/realtime?period=daily` |

#### 成本趋势

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/costs/trend?period=daily&days=30` |

#### 成本分解

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/costs/breakdown?group_by=model` |

`group_by` 取值: `model` / `agent` / `provider` / `task`

---

### 预算告警

#### 创建告警

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/llm/costs/alerts` |

```json
{"threshold": 10.0, "period": "monthly", "dimension": "total"}
```

#### 获取告警列表

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/costs/alerts?is_enabled=true` |

#### 删除告警

| 属性 | 值 |
|------|-----|
| **Method** | DELETE |
| **Path** | `/llm/costs/alerts/{alert_id}` |

#### 检查触发告警

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/costs/alerts/check` |

---

### Token 统计

#### Token 摘要

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/tokens/summary?agent_id=xxx&model=xxx` |

#### Token 历史

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/tokens/history?period=daily&days=30` |

---

### 缓存统计

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/llm/cache/stats` |

---

## 相关文档

- [LLM 服务模块](../04-modules/backend/llm-service.md)
