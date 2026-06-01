# 记忆模型

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：记忆数据结构定义
- **代码路径**：`backend/app/models/memory_db.py`

---

## 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 记忆唯一标识 |
| `agent_id` | string | 所属 Agent |
| `session_id` | string | 会话 ID（可选） |
| `content` | text | 记忆内容 |
| `level` | string | 记忆层级 |
| `tags` | List[string] | 标签列表 |
| `relevance_score` | float | 相关性分数 |
| `usage_count` | int | 使用次数 |
| `source` | string | 来源 |
| `extra_data` | JSON | 额外元数据 |
| `created_at` | datetime | 创建时间 |
| `last_accessed_at` | datetime | 最后访问时间 |

---

## 记忆层级

| 层级 | 值 | 说明 |
|------|-----|------|
| L1 | `working` | 工作记忆 - 当前会话 |
| L2 | `short_term` | 短期记忆 - 最近会话摘要 |
| L3 | `long_term` | 长期记忆 - 持久化知识 |

---

## 模型类

### MemoryEntryModel

```python
class MemoryEntryModel(Base):
    __tablename__ = "memory_entries"
    
    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    content = Column(Text, nullable=False)
    level = Column(String, nullable=False, default="working")
    tags = Column(JSON, default=list)
    relevance_score = Column(Float, default=1.0)
    usage_count = Column(Integer, default=0)
    source = Column(String, nullable=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now)
    last_accessed_at = Column(DateTime, default=datetime.now)
```

### AgentContextModel

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_id` | string | Agent ID（主键） |
| `session_id` | string | 会话 ID |
| `role` | string | 角色 |
| `system_prompt` | text | 系统提示词 |
| `personality` | JSON | 性格配置 |
| `status` | string | 状态 |
| `current_task` | string | 当前任务 |
| `task_progress` | float | 任务进度 |
| `max_context_tokens` | int | 最大上下文 token 数 |

---

## 相关文档

- [记忆服务](../memory-service.md)
- [记忆系统设计](../../../02-design/memory-system.md)