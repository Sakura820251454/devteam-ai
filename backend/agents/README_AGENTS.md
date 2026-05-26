# Agent Soul 文件系统

基于 `soul.md` 文件定义 Agent 行为准则的轻量级系统。受 [nanobot](https://github.com/HKUDS/nanobot) 启发，核心思想是"原则驱动行为"——每个 Agent 通过一组核心原则和执行规则来定义其工作方式，而非预设具体角色。

## 目录结构

```
agents/
├── README_AGENTS.md
├── agent_xiaowang/
│   └── soul.md
├── agent_xiaoli/
│   └── soul.md
├── agent_xiaochen/
│   └── soul.md
├── agent_xiaoliu/
│   └── soul.md
├── agent_xiaozhang/
│   └── soul.md
├── agent_xiaozhao/
│   └── soul.md
├── agent_mu/
│   └── soul.md
├── agent_ning/
│   └── soul.md
└── agent_heng/
    └── soul.md
```

## soul.md 文件格式

每个 `soul.md` 包含两个核心段落，以及可选的扩展段落。Agent 的名称从目录名中自动提取（去掉 `agent_` 前缀）。

### 核心段落

```markdown
# Agent Soul

## Core Principles

- 原则1：描述这个 Agent 的核心信念
- 原则2：...
- ...

## Execution Rules

- 规则1：描述具体执行时遵循的规则
- 规则2：...
- ...
```

### 可选扩展段落

解析器会识别以下可选段落，内容会附加到系统提示词中：

- **## Skills** — 能力描述
- **## Knowledge** — 知识领域
- **## Boundaries** — 行为边界

```markdown
## Skills
- 代码审查：善于发现逻辑漏洞和潜在问题
- 技术调研：快速评估新技术的适用性

## Boundaries
- 不修改生产环境配置
- 不在没有 review 的情况下提交核心模块代码
```

## 实际示例

项目中已包含多个 Agent，以下是其中一个：

```markdown
# Agent Soul

## Core Principles

- 解决实际问题，而不是描述解决方案。
- 保持简洁，除非用户需要深入讨论。
- 知道就是知道，不知道就说不知道，绝不不懂装懂。
- 遇到问题先动手排查，排查不出来再用工具查找，实在找不到才问用户。
- 把用户的信任当作最宝贵的资产。

## Execution Rules

- 单步任务立即执行，不要只是计划或承诺。
- 多步任务先列出计划，等用户确认后再执行。
- 写代码前先读代码，不假设文件存在或内容正确。
- 工具调用失败时，先诊断错误并尝试其他方法，再报告失败。
- 多步修改后验证结果（重新读取文件、运行测试、检查输出）。
```

## 数据模型

### SoulFile

解析后的数据结构（`app/services/shared/soul_parser.py`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | Agent 名称（从目录名提取） |
| role | str | 角色描述（可选） |
| title | str | 标题（可选） |
| avatar_emoji | str | 头像表情（可选） |
| avatar_color | str | 头像颜色，默认 `#6B7280` |
| core_principles | List[str] | 核心原则列表 |
| execution_rules | List[str] | 执行规则列表 |
| role_definitions | Dict[str, str] | 扩展段落（Skills, Knowledge, Boundaries） |

## 快速开始

### 1. 加载单个 Agent

```python
from app.services.shared.soul_parser import load_agent_from_soul, soul_to_system_prompt

soul = load_agent_from_soul("agents/agent_xiaowang/soul.md")
system_prompt = soul_to_system_prompt(soul)
print(system_prompt)
```

### 2. 批量加载所有 Agent

```python
from app.services.shared.soul_parser import load_all_agents

agents = load_all_agents("agents")
for name, soul in agents.items():
    print(f"{name}: {len(soul.core_principles)} 条原则, {len(soul.execution_rules)} 条规则")
```

### 3. 运行测试

```bash
cd backend
python test_soul_parser.py
```

## 系统集成

soul.md 在整个系统中被多处消费，以下是主要集成点：

### AgentService — 自动加载

`AgentService` 启动时自动从 `agents/` 目录加载所有 soul.md 并注册为可用的 Agent 实例（`app/services/agent/agent_service.py:_load_from_soul_files`）。无需手动配置。

### AgentTraitService — LLM 能力画像

`AgentTraitService` 读取 soul 数据，通过 LLM 为每个 Agent 生成结构化的能力画像（技能标签、优势领域、协作风格），用于任务匹配（`app/services/agent/agent_trait_service.py`）。

```python
from app.services.agent.agent_trait_service import agent_trait_service

traits = await agent_trait_service.ensure_traits("xiaowang")
print(traits.skills, traits.collaboration_style)
```

### AgentContextFactory — 上下文创建

从 SoulFile 创建 Agent 的独立上下文，包含系统提示词和人格数据（`app/models/agent_context.py:AgentContextFactory.from_soul_file`）。

### Prompt Registry — 提示词渲染

`soul_to_system_prompt()` 通过 prompt registry 渲染输出，提示词模板定义在 `app/prompts/registry.yaml` 中（`shared.soul.header`、`shared.soul.core_principles`、`shared.soul.execution_rules`、`shared.soul.fallback`）。修改模板后无需改代码。

## 创建新 Agent

1. 在 `agents/` 下创建 `agent_<name>/` 目录
2. 创建 `soul.md`，写入 `## Core Principles` 和 `## Execution Rules`
3. 可选添加 `## Skills`、`## Knowledge`、`## Boundaries` 段落
4. 重启后端，AgentService 会自动加载

## API 参考

### `load_agent_from_soul(soul_file_path: str) -> SoulFile`

从单个 soul.md 文件加载 Agent 定义。

### `load_all_agents(agents_dir: str = "agents") -> Dict[str, SoulFile]`

批量加载目录下所有 Agent。跳过没有 soul.md 的目录，解析失败时打印错误但不中断。

### `soul_to_system_prompt(soul: SoulFile) -> str`

将 SoulFile 转换为 LLM 系统提示词。通过 prompt registry 渲染各段落，无 soul 数据时使用 fallback 模板。

### `AgentService.create_agent_from_soul(soul_name: str, name: str = None) -> Dict`

直接从 soul.md 创建 Agent 实例并注册到系统中。

### `AgentService.get_soul_based_agents() -> List[Dict]`

获取所有基于 soul.md 的 Agent 实例。

## 设计理念

1. **原则驱动**：通过核心原则和执行规则定义行为，不预设具体职业角色
2. **文件即配置**：一个目录 + 一个 soul.md = 一个 Agent，零代码添加
3. **自动加载**：AgentService 启动时自动发现并注册
4. **LLM 增强**：AgentTraitService 用 LLM 从 soul 数据动态分析能力画像
5. **Prompt Registry 集成**：提示词模板集中管理，修改渲染逻辑无需改代码
