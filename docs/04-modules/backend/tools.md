# Agent 工具系统

**版本**: v1.0
**最后更新**: 2026-05-26

---

## 概述

- **功能定位**：Agent 工具调用能力，对标 Claude Code 的工具风格。LLM 自主决策调用什么工具、传什么参数，框架负责执行。
- **所属层级**：backend
- **代码路径**：`backend/app/services/agent/tools.py`、`backend/app/services/agent/tool_executor.py`

---

## 设计理念

采用 OpenAI function calling 格式（DeepSeek 兼容），每个工具由 `ToolDef` 定义：name / description / parameters (JSON Schema) / fn (async callable)。

Agent 看到工具描述后自主决定是否调用、调用哪个、传什么参数。`project_id` 由框架自动注入，LLM 不可见。

---

## 核心组件

### ToolDef（tools.py）

| 字段 | 说明 |
|------|------|
| `name` | 工具名称（LLM 看到的标识符） |
| `description` | 功能描述 + 使用场景提示（帮助 LLM 判断何时调用） |
| `parameters` | JSON Schema 定义入参（不包含 project_id） |
| `fn` | Python async callable `(project_id, **kwargs) -> str` |

方法：
- `to_openai()` — 导出为 OpenAI function calling 格式

### ToolRegistry（tools.py）

| 方法 | 说明 |
|------|------|
| `register(tool: ToolDef)` | 注册工具 |
| `get(name)` | 获取单个工具定义 |
| `get_openai_tools()` | 导出所有工具为 OpenAI 格式列表 |
| `execute(name, args, project_id)` | 执行工具调用（自动 await 异步函数） |

### ToolExecutor（tool_executor.py）

| 字段/方法 | 说明 |
|-----------|------|
| `registry` | ToolRegistry 实例 |
| `max_iterations` | 最大迭代次数（默认 8） |
| `run(messages, tools, project_id, cancellation_token)` | 工具调用循环 |

---

## 雏形阶段工具（5 个）

| 工具名 | 对标 Claude Code | 功能 |
|--------|-----------------|------|
| `list_files` | Glob | 列出项目工作区文件，支持 glob 模式匹配 |
| `read_file` | Read | 读取指定文件内容，支持行范围分页 |
| `write_file` | Write | 写入/覆盖文件到工作区 |
| `search_content` | Grep | 在工作区文件中正则搜索，返回文件:行号:内容 |
| `run_command` | Bash | 在工作区目录中执行 shell 命令（30s 超时） |

---

## 工具调用循环

```
agent_executor._fallback_single_execution()
  │
  └─► ToolExecutor.run(messages, tools, project_id)
        │
        ├── 1. 调用 LLM（带 tools 定义）
        ├── 2. LLM 返回 text → 直接返回最终结果 ✓
        └── 3. LLM 返回 tool_calls → 循环:
               │
               ├── 将 assistant 消息（含 tool_calls）追加到对话
               ├── asyncio.gather 并行执行所有 tool_call
               ├── 将 tool 结果作为 Message(role="tool") 追加
               └── 再次调用 LLM（最多 8 轮）
                    │
                    └── 达到 max_iterations → 强制要求总结
```

---

## LLM Provider 适配

4 个 Provider 均支持 `tools` 参数：

| Provider | 格式 |
|----------|------|
| DeepSeek | OpenAI 兼容格式，直接透传 |
| OpenAI | 原生格式 |
| Azure OpenAI | 同 OpenAI |
| Anthropic | 内部转换：tool_use content blocks → OpenAI 格式 tool_calls |

---

## 依赖关系

- 依赖：WorkspaceManager（文件/命令操作）、LLMService（带 tools 参数的 LLM 调用）
- 被依赖：AgentExecutor._fallback_single_execution

---

## 相关文档

- [Agent 执行器](./agent-executor.md)
- [LLM 服务](./llm-service.md)
- [工作区管理](./project-service.md)
- [Prompt 架构](../../02-design/prompt-architecture.md)
