# Agent 模型

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：Agent 数据结构定义
- **代码路径**：`backend/app/models/agent.py`

---

## 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | Agent 唯一标识 |
| `config` | AgentConfig | Agent 配置对象 |
| `status` | enum | 状态 |
| `current_task` | string | 当前任务 ID（可选） |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

---

## AgentConfig 配置字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | Agent 名称 |
| `role` | string | Agent 角色 |
| `title` | string | 职称 |
| `backstory` | string | 背景故事 |
| `personality_type` | enum | 性格类型 |
| `communication_style` | enum | 沟通风格 |
| `confidence` | int | 自信度 (0-100) |
| `proactivity` | int | 积极性 (0-100) |
| `skills` | Dict[string, SkillLevel] | 技能列表 |
| `knowledge_areas` | List[string] | 知识领域 |
| `task_preferences` | List[string] | 任务偏好 |
| `max_messages_per_round` | int | 每轮最多发言次数 |
| `min_interval` | int | 最短发言间隔(秒) |
| `can_multi_task` | bool | 是否可兼任 |
| `llm_config` | LLMConfig | LLM 配置（可选） |

---

## 状态枚举

```python
class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    STOPPED = "stopped"
```

---

## 性格类型枚举

```python
class PersonalityType(str, Enum):
    RIGOROUS = "严谨型"
    CREATIVE = "创意型"
    PRAGMATIC = "务实型"
    COLLABORATIVE = "协作型"
```

---

## 沟通风格枚举

```python
class CommunicationStyle(str, Enum):
    CONCISE = "简洁直接"
    DETAILED = "详细解释"
    HUMOROUS = "幽默风趣"
```

---

## 技能等级枚举

```python
class SkillLevel(str, Enum):
    MASTERED = "精通"
    PROFICIENT = "熟练"
    FAMILIAR = "了解"
```

---

## 相关文档

- [Agent 服务](../agent-service.md)
- [Agent 模型设计](../../../02-design/agent-model.md)