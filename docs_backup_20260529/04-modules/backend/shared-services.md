# 共享服务模块

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

- **功能定位**：跨模块共享的基础设施服务（Soul 解析、批处理与重试）
- **所属层级**：backend
- **代码路径**：`backend/app/services/shared/`

---

## 核心组件

### SoulParser (`soul_parser.py`)

解析 `agents/*/soul.md` 文件，提取 Agent 的灵魂定义。

**SoulFile 数据结构**：

| 字段 | 说明 |
|------|------|
| `name` | Agent 名称 |
| `role` | 角色 |
| `title` | 头衔 |
| `core_principles` | 核心原则列表 |
| `execution_rules` | 执行规则列表 |
| `role_definitions` | 额外角色定义 |

**解析流程**：
1. 从目录名提取 Agent 名字（`agent_xiaozhang` → `xiaozhang`）
2. 解析 YAML frontmatter 获取元数据
3. 解析 Markdown 章节获取核心原则和执行规则

### BatchProcessor (`batch_retry.py`)

批处理器，提供批量操作和并发控制。

| 方法 | 说明 |
|------|------|
| `process_batch(items, processor)` | 批量处理（带信号量并发控制） |

### RetryConfig (`batch_retry.py`)

重试配置，支持指数退避。

| 字段 | 说明 |
|------|------|
| `max_retries` | 最大重试次数（默认 3） |
| `initial_delay` | 初始延迟（默认 1.0s） |
| `max_delay` | 最大延迟（默认 60.0s） |
| `exponential_base` | 指数退避基数（默认 2.0） |

---

## 依赖关系

- SoulParser 被 AgentService 依赖
- BatchProcessor 被 Memory 服务依赖
