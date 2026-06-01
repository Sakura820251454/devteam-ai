# 持久化层

**版本**: v3.1
**最后更新**: 2026-05-20

---

## 概述

- **功能定位**: 为项目、流水线、任务、会话、消息提供完整的数据库持久化，确保服务器重启和页面刷新后核心状态不丢失
- **所属层级**: backend
- **代码路径**:
  - `backend/app/models/core_db.py` — ORM 模型定义
  - `backend/app/services/persistence/` — 持久化 CRUD 服务
  - `backend/app/database/__init__.py` — 数据库引擎与会话管理

---

## 设计背景

### 问题

v3.0 之前，项目、流水线、任务、会话、消息全部存储在 Python 字典中（内存），服务器重启或页面刷新后全部丢失：

| 服务 | 存储方式 | 持久化 |
|------|---------|--------|
| ProjectService | `Dict[str, Project]` | 无 |
| PipelineOrchestrator | `Dict[str, Pipeline]` | 无 |
| TaskBoard | `Dict[str, Dict[str, Task]]` | 无 |
| AgentService (sessions) | `Dict[str, Session]` | 无 |

只有 `TaskPersistenceService` 管理的 `task_executions` 和 `task_checkpoints` 表有 SQLite 持久化。

### 方案

采用 **写穿（write-through）模式**：

1. **SQLite 存结构化状态** — 项目、流水线、任务、会话、消息
2. **每次修改同时写内存和 DB** — 内存读快，DB 保证持久
3. **启动时从 DB 全量加载到内存** — 服务启动后数据即刻可用
4. **文件系统存产物** — artifacts、src、docs 等大文件仍由 WorkspaceManager 管理

---

## 数据模型

### 核心表（5 张新表）

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `projects` | `ProjectModel` | 项目元数据（名称、描述、状态、阶段、团队配置） |
| `pipelines` | `PipelineModel` | 流水线状态（阶段、进度、Agent、上下文、日志） |
| `tasks` | `TaskModel` | 任务看板（标题、状态、优先级、分配、历史） |
| `sessions` | `SessionModel` | 会话元数据（标题、参与者、Token 预算） |
| `messages` | `MessageModel` | 会话消息（发送者、内容、类型、时间戳） |

### 字段类型约定

- **主键**: 所有表使用 `String` UUID 主键（应用层生成）
- **JSON 字段**: 列表/字典使用 SQLAlchemy `JSON` 类型，SQLite 存为 JSON 文本，PostgreSQL 使用 JSONB
- **时间戳**: 使用 `DateTime` 列，`created_at` 有默认值 `datetime.now`
- **索引**: 对 `project_id`、`status`、`session_id` 等常用查询列建立索引

### 数据模型文件

`backend/app/models/core_db.py` 包含所有 5 个 ORM 模型，遵循与 `execution_db.py`、`memory_db.py` 相同的模式。

---

## 持久化服务

所有持久化服务位于 `backend/app/services/persistence/`，遵循统一的单例模式：

| 服务类 | 文件 | 职责 |
|--------|------|------|
| `ProjectPersistenceService` | `project_persistence.py` | 项目 CRUD |
| `TaskPersistenceService` | `task_persistence.py` | 任务 CRUD |
| `PipelinePersistenceService` | `pipeline_persistence.py` | 流水线 CRUD |
| `SessionPersistenceService` | `session_persistence.py` | 会话+消息 CRUD |

### 统一接口

每个持久化服务遵循相同的生命周期：

```python
class XxxPersistenceService:
    def __init__(self):
        self._session_maker = None

    def initialize(self, session_maker):
        """注入异步 SQLAlchemy 会话工厂"""

    async def load_all(self) -> Dict[str, DomainObject]:
        """全量加载 → 内存字典"""

    async def save(self, obj) -> None:
        """Upsert：查询已有 → 原地更新或新建 → commit"""

    async def delete(self, id) -> None:
        """按 ID 删除"""
```

### 转换函数

每个服务包含私有转换函数，在 ORM 模型和领域模型之间转换：

- `_model_from_xxx(domain)` — 领域对象 → ORM 模型（写入用）
- `_xxx_from_model(model)` — ORM 模型 → 领域对象（读取用）

### Pipeline 特殊处理

`PipelinePersistenceService.load_all()` 在加载时将状态为 `running` 或 `paused` 的流水线标记为 `failed`，因为其 asyncio 任务在服务器重启后已失效：

```python
if pipeline.status in (PipelineStatus.RUNNING, PipelineStatus.PAUSED):
    pipeline.status = PipelineStatus.FAILED
    pipeline.add_log("control", "Pipeline marked as FAILED: server restarted")
```

`save()` 方法将日志截断至最近 1000 条，防止 JSON 列无限增长。

---

## 启动流程

`backend/app/main.py` 的 `lifespan` 中按顺序初始化：

```
1. init_db()                              → 创建所有表
2. 初始化 persistence 服务（注入 session maker）
3. 注入到业务服务：
   project_service.initialize(project_persistence)
   task_board.initialize(task_persistence)
   pipeline_orchestrator.initialize(pipeline_persistence)
   agent_service.initialize(session_persistence)
4. load_all() 加载持久化数据到内存：
   await project_service.load_all()
   await task_board.load_all()
   await pipeline_orchestrator.load_all()
   await agent_service.load_all_sessions()
5. 初始化其他服务（stuck_detector 等）
```

---

## 业务服务集成

每个业务服务的写操作方法变为 `async`，末尾调用持久化服务：

| 服务 | 异步化方法 |
|------|-----------|
| `ProjectService` | `create_project`, `update_project`, `delete_project`, `advance_phase` |
| `TaskBoard` | `create_task`, `update_task`, `assign_agents`, `change_status`, `add_comment`, `delete_task`, `clear_project_tasks` |
| `PipelineOrchestrator` | `create_pipeline`, `start_pipeline`, `pause_pipeline`, `resume_pipeline`, `stop_pipeline`（已异步，增加 save 调用）；`_run_pipeline` 各阶段完成后自动保存 |
| `AgentService` | `create_session`（异步化）；`agent_chat` / `agent_chat_stream` 中每条消息追加后保存 |

---

## 持久化 vs 瞬态

| 持久化（DB） | 瞬态（重启后重建） |
|-------------|-------------------|
| 项目 (projects) | asyncio task handles |
| 流水线 (pipelines) | cancellation tokens |
| 任务 (tasks) | MessageBus subscribers |
| 会话 (sessions) | SpeakingController 队列 |
| 消息 (messages) | AgentExecutor running_tasks |
| 任务执行 (task_executions)* | SecurityGuard 计数器 |
| 任务检查点 (task_checkpoints)* | LLMService provider_cache |

\* 由原有的 `TaskPersistenceService` 管理，本次未改动

---

## 相关文档

- [TaskPersistenceService 参考实现](/04-modules/backend/execution-persistence) — 原有执行状态持久化
- [项目结构](/03-development/structure) — 代码组织
- [Pipeline 编排器](/04-modules/backend/pipeline-orchestrator)
- [任务看板](/04-modules/backend/task-board)
- [项目管理](/04-modules/backend/project-service)
