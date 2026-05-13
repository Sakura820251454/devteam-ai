# Agent Soul 文件系统

基于 `soul.md` 文件定义 Agent 独特个性的系统，受 [nanobot](https://github.com/HKUDS/nanobot) 和多个 Agent 项目启发。

## 📁 目录结构

```
agents/
├── agent_xiaowang/
│   └── soul.md
├── agent_xiaoli/
│   └── soul.md
└── agent_zhangsan/
    └── soul.md
```

## 📝 soul.md 文件格式

每个 Agent 都有独立的 `soul.md` 文件，定义其独特个性、技能、背景等。

### 基本结构

```markdown
## Basic Information
**name**: 小王
**role**: 后端开发工程师
**title**: 中级工程师
**avatar_emoji**: 👨‍💻
**avatar_color**: #10B981

## Personality
**type**: 严谨型
**communication_style**: 详细解释
**confidence**: 85
**proactivity**: 75

### Personality Description
我是一个细心、话多、喜欢讨论的人...

### Speech Style
- 说话比较详细，喜欢解释清楚来龙去脉
- 有时会主动提问，引导讨论深入...

## Background
**work_years**: 3
**education**: 计算机科学与技术专业 本科

### Backstory
在一家互联网公司工作了3年...

### Work History
- 2023年：主导订单系统重构
- 2024年：设计并实现了新的支付网关系统

## Skills

### Technical Skills
- **Python**: 精通 - 我的主要开发语言
- **FastAPI**: 精通 - 项目主力框架
- **SQL/数据库**: 熟练

### Soft Skills
- 代码审查 - 喜欢通过CR互相学习
- 架构讨论 - 热衷于技术选型

## Knowledge Areas
后端架构, API设计, 数据库优化

## Task Preferences

### 喜欢的任务类型
1. 架构设计和技术选型
2. 性能优化和重构

### 不喜欢的任务类型
- 重复的CRUD操作
- 纯UI交互开发

## Collaboration Style
在团队中的角色：
- 作为后端开发，我喜欢在需求阶段就参与进来...

## System Prompt Template
你是一位名为{name}的{role}...
```

## 🚀 快速开始

### 1. 加载单个 Agent

```python
from app.services.soul_parser import load_agent_from_soul, soul_to_system_prompt

# 加载 Agent
soul = load_agent_from_soul("agents/agent_xiaowang/soul.md")

# 生成系统提示词
system_prompt = soul_to_system_prompt(soul)
print(system_prompt)
```

### 2. 批量加载所有 Agents

```python
from app.services.soul_parser import load_all_agents

# 加载所有 Agent
agents = load_all_agents("agents")

for name, soul in agents.items():
    print(f"{name}: {soul.role}")
```

### 3. 运行测试

```bash
cd backend
venv\Scripts\python.exe test_soul_parser.py
```

## 🎯 字段说明

### Basic Information

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | Agent 名字 |
| role | string | 角色（后端开发、前端开发等） |
| title | string | 职称（初级、中级、高级等） |
| avatar_emoji | string | 头像表情 |
| avatar_color | string | 头像颜色（十六进制） |

### Personality

| 字段 | 类型 | 说明 |
|------|------|------|
| type | enum | 性格类型（严谨型、创意型、务实型、协作型） |
| communication_style | enum | 沟通风格（简洁直接、详细解释、幽默风趣） |
| confidence | int | 自信度 (0-100) |
| proactivity | int | 积极性 (0-100) |

### Background

| 字段 | 类型 | 说明 |
|------|------|------|
| work_years | int | 工作年限 |
| education | string | 教育背景 |

### Skills

技能分为 Technical Skills（技术技能）和 Soft Skills（软技能）。

技术技能格式：
```markdown
- **技能名**: 等级 - 描述
```

等级选项：精通、熟练、了解

### Task Preferences

分为喜欢的任务和不喜欢的任务两部分。

## 💡 设计理念

参考多个 Agent 项目的最佳实践：

1. **文件驱动**：Agent 的所有属性在 Markdown 文件中定义，易于修改和版本控制
2. **个性突出**：每个 Agent 有独特的个性、说话风格、技能背景
3. **易于扩展**：可以通过增加新的 `agent_xxx/` 目录添加新 Agent
4. **模板化**：通过 `System Prompt Template` 统一生成系统提示词

## 📚 示例

项目已包含两个示例 Agent：

1. **小王** - 后端开发工程师，严谨型，细心话多
2. **小李** - 全栈开发工程师，务实型，低调高效

## 🛠️ 创建新 Agent

1. 在 `agents/` 目录下创建新目录 `agent_name/`
2. 在新目录下创建 `soul.md` 文件
3. 复制模板文件并修改内容
4. 运行测试验证解析成功

## 🔌 API 接口

### `load_agent_from_soul(soul_file_path: str) -> SoulFile`

从单个 soul.md 文件加载 Agent 定义。

### `load_all_agents(agents_dir: str = "agents") -> Dict[str, SoulFile]`

从 agents 目录批量加载所有 Agent。

### `soul_to_system_prompt(soul: SoulFile) -> str`

将 SoulFile 对象转换为系统提示词。
