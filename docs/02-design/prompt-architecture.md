# Prompt 架构设计

**版本**: v2.4  
**日期**: 2026-05-22  
**状态**: 已实现

---

## 1. 核心设计决策

**Prompt 与代码分离**：所有 LLM prompt 模板从 Python f-string 迁移到统一注册表 `backend/app/prompts/registry.yaml`。代码通过 `registry.render(id, vars)` 调用，prompt 文字不再硬编码在源码中。

**设计原则**：Agent 的身份和技能全部由 soul.md 定义、trait_service 动态分析，不在 prompt 中预设角色。

---

## 2. Prompt Registry 系统

### 架构

```
backend/app/prompts/registry.yaml    ← 唯一真相源（47 条 prompt 模板）
backend/app/services/shared/
  prompt_registry.py                 ← PromptRegistry 类（惰性加载、render、validate）
scripts/prompt_doc_gen.py            ← 自动生成 VitePress 文档 + --check CI 模式
docs/04-modules/backend/
  prompt-registry.md                 ← 自动生成的 prompt 清单文档
```

### 命名规范

```
{module}.{file_short}.{purpose}[.{variant}]
```

示例：
- `agent.executor.plan_steps` — agent 模块 / executor 文件 / 任务规划
- `agent.executor.step_prompt.first` — 同文件 / 步骤执行 / 第一步骤（变体）
- `collaboration.discussion.agent_speak` — collaboration 模块 / discussion 文件 / 发言
- `execution.checkpoint.resume_context` — execution 模块 / checkpoint 文件 / 恢复执行

### 使用方式

```python
from app.services.shared.prompt_registry import registry

prompt = registry.render("agent.executor.plan_steps", {
    "task_title": task.title,
    "task_description": task.description,
})
```

LLM 收到的字符串与迁移前逐字节相同，零功能影响。

---

## 3. 条件 Prompt 处理策略

部分 prompt 需要根据运行时状态生成不同的内容。按复杂度分四种策略：

| 策略 | 适用场景 | 示例 |
|------|----------|------|
| **拆分为独立条目** | 简单二元条件 | `step_prompt.first` / `step_prompt.continue`（有无前置步骤） |
| **变量驱动** | 简单内联条件 | `final_instruction` 变量（最后一轮加特殊指令） |
| **分段模板** | 若干可选段落拼接 | `build_system_prompt` 的 5 个可选子段（intro/backstory/skills/knowledge/footer） |
| **代码管理** | 复杂多分支（5+ 条件） | `feedback_context`（依赖 workspace 数据、stages、消息历史等） |

代码管理类 prompt 在 registry 中标记 `code_managed: true`，注册表只记录信息（描述、源文件、变量），不提供 `render()`。

---

## 4. Agent 角色定义策略

### 主路径：soul.md → trait_service

Agent 的**性格和原则**由 `soul.md` 定义（6 个 Agent：小刘、小尘、小王、小张、小赵、小李）。

Agent 的**角色标签**（如"后端开发""架构师"）由 `agent_trait_service.py` 通过 LLM 分析 soul.md 动态生成，随项目上下文变化，不硬编码。

### 兜底路径：通用模板

当所有 soul.md 均不可用时，使用 `agent_service.py` 中的一个**通用兜底模板**（v2.4 从 6 个角色预设模板合并为 1 个）：

```
你是 DevTeam AI 开发团队的一员。

保持简洁，直接解决问题。
遇到问题先动手排查，排查不出来再用工具查找，实在找不到才问用户。
```

`capabilities=[]`，`collaboration_style` 和 `speaking_tendency` 均为通用默认值，不预设具体角色。

### 设计理由

预设角色（"你是一位后端开发工程师"）会与"在分配任务之前不预设身份"的原则冲突。Agent 的身份应由其实际能力和当前任务动态决定，而非模板预先写死。

---

## 5. CI 与文档同步

每次 PR 在 CI 中运行两步校验：

1. **Registry 自校验**：`registry.validate()` 检查每条 prompt 声明的变量与模板中实际使用的 `{var}` 是否一致
2. **文档同步检查**：`prompt_doc_gen.py --check` 确保 `prompt-registry.md` 与 `registry.yaml` 内容一致

---

## 6. 相关文件索引

| 文件 | 用途 |
|------|------|
| `backend/app/prompts/registry.yaml` | 所有 prompt 模板的唯一真相源 |
| `backend/app/services/shared/prompt_registry.py` | PromptRegistry 类 |
| `backend/app/services/agent/agent_service.py` | 通用兜底模板（`get_preset_templates`） |
| `backend/agents/*/soul.md` | Agent 灵魂定义（性格/原则/执行规则） |
| `backend/app/services/agent/agent_trait_service.py` | 从 soul.md 动态生成角色标签 |
| `scripts/prompt_doc_gen.py` | 文档生成器 |
| `docs/04-modules/backend/prompt-registry.md` | 自动生成的 prompt 清单 |
