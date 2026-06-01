# 知识进化 API

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

知识资产管理接口，支持知识提取、搜索、使用追踪、模式发现和技能生成。

**Base Path**: `/knowledge`

---

## 接口列表

### 知识发现与记录

#### 从内容中提取知识

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/knowledge/discover?content=xxx&agent_id=xxx&task_type=xxx` |

#### 记录成功案例

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/knowledge/success-case` |

```json
{
  "task_description": "...",
  "context": "...",
  "method": "...",
  "effect": "...",
  "success_factors": ["..."],
  "agent_id": "xxx"
}
```

#### 记录失败教训

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/knowledge/failure-lesson` |

#### 添加代码片段

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/knowledge/code-snippet` |

---

### 知识查询

#### 搜索知识

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/knowledge/search?query=xxx&knowledge_type=explicit&limit=10` |

#### 获取知识详情

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/knowledge/{knowledge_id}` |

#### 标记使用情况

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/knowledge/{knowledge_id}/use?success=true` |

---

### 模式与技能

#### 发现模式

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/knowledge/patterns/discover` |

#### 获取所有模式

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/knowledge/patterns` |

#### 生成技能

| 属性 | 值 |
|------|-----|
| **Method** | POST |
| **Path** | `/knowledge/skills/generate?agent_id=xxx` |

#### 获取所有技能

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/knowledge/skills` |

#### 获取统计

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/knowledge/stats` |

---

## 相关文档

- [知识服务模块](../04-modules/backend/knowledge-service.md)
- [自我学习设计](../02-design/self-learning.md)
