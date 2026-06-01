# PilotDeck Code Wiki

## 项目概述

**PilotDeck** 是一个面向任务的 AI Agent 生产力平台，以 WorkSpace 为核心概念重新定义代理操作边界和内存演进。它由清华大学 THUNLP、ModelBest、OpenBMB 和 AI9Stars 联合开发开源。

### 核心特性

| 特性 | 描述 |
|------|------|
| **WorkSpace 级别隔离** | 每个项目拥有独立的文件系统、内存存储和技能集 |
| **白盒可追溯内存** | 内存生成、提取、存储和检索全程可见，支持编辑和回滚 |
| **智能路由** | 自动检测任务难度，匹配合适的模型，显著降低成本 |
| **始终在线执行** | 后台自动发现任务、运行监控、交付成果 |
| **MCP 原生支持** | 原生支持 Model Context Protocol，跨前端一致性 |

---

## 项目架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PilotDeck 架构                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
│  │   CLI/TUI   │   │   Web UI    │   │   Feishu    │   │   Discord   │ │
│  │   终端接口   │   │   网页界面   │   │   飞书渠道   │   │   社交渠道   │ │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘ │
│         │                  │                  │                  │        │
│         └──────────────────┼──────────────────┼──────────────────┘        │
│                            ▼                                             │
│                   ┌─────────────────┐                                   │
│                   │   Gateway层     │ ← 会话路由、事件分发、权限控制        │
│                   │   (网关服务)     │                                   │
│                   └────────┬────────┘                                   │
│                            ▼                                             │
│         ┌──────────────────┼──────────────────┐                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
│  │   Agent层   │   │  Router层   │   │   Tool层    │                   │
│  │  (代理运行)  │   │  (智能路由)  │   │  (工具执行)  │                   │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘                   │
│         │                  │                  │                          │
│         └──────────────────┼──────────────────┘                          │
│                            ▼                                             │
│                   ┌─────────────────┐                                   │
│                   │   Model层      │ ← 模型调用、多模态支持、错误处理      │
│                   │   (模型运行)    │                                   │
│                   └─────────────────┘                                   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    扩展系统 (Extension)                        │       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │       │
│  │  │ Plugins │  │  Hooks  │  │ Skills  │  │ Cron    │        │       │
│  │  │  (插件)  │  │ (钩子)  │  │ (技能)  │  │(定时任务)│        │       │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    上下文系统 (Context)                        │       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │       │
│  │  │ Memory  │  │Budget   │  │Compaction│ │Recovery │        │       │
│  │  │ (内存)   │  │(预算)   │  │ (压缩)   │ │(恢复)   │        │       │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
PilotDeck/
├── src/                              # 核心源代码
│   ├── agent/                        # 代理运行时核心
│   │   ├── loop/                     # 代理循环逻辑
│   │   ├── protocol/                 # 协议定义
│   │   ├── runtime/                  # 运行时配置
│   │   ├── session/                  # 会话管理
│   │   ├── sub/                      # 子代理支持
│   │   └── turn/                     # 轮次执行
│   ├── adapters/                     # 多渠道适配器
│   │   ├── channel/                  # 消息渠道 (Feishu/Discord/Webhook等)
│   │   └── web/                      # Web相关适配
│   ├── always-on/                    # 后台执行系统
│   │   ├── config/                   # 配置解析
│   │   ├── context/                  # 上下文管理
│   │   ├── contracts/                # 契约定义
│   │   ├── protocol/                 # 协议
│   │   ├── runtime/                  # 运行时
│   │   ├── storage/                  # 存储
│   │   ├── tool/                     # 工具
│   │   ├── web/                      # Web服务
│   │   └── workspace/                # 工作空间
│   ├── cli/                          # 命令行接口
│   ├── context/                      # 上下文系统
│   │   ├── attachments/              # 附件处理
│   │   ├── budget/                   # 预算管理
│   │   ├── compaction/               # 消息压缩
│   │   ├── extension/                # 扩展解析
│   │   ├── input/                    # 输入处理
│   │   ├── instructions/             # 指令发现
│   │   ├── memory/                   # 内存系统
│   │   ├── projection/               # 消息投影
│   │   └── prompt/                   # 提示词组装
│   ├── cron/                         # 定时任务
│   │   ├── config/                   # 配置
│   │   ├── protocol/                 # 协议
│   │   ├── runtime/                  # 运行时
│   │   ├── storage/                  # 存储
│   │   └── tool/                     # 工具
│   ├── extension/                    # 扩展系统
│   │   ├── contributions/            # 贡献类型定义
│   │   ├── hooks/                    # 钩子系统
│   │   └── plugins/                  # 插件系统
│   ├── gateway/                      # 网关服务
│   │   ├── client/                   # 客户端
│   │   ├── elicitation/              # 引导服务
│   │   ├── permission/               # 权限管理
│   │   ├── protocol/                 # 协议
│   │   └── server/                   # 服务端
│   ├── lifecycle/                    # 生命周期管理
│   ├── mcp/                          # MCP协议支持
│   ├── model/                        # 模型管理
│   │   ├── catalog/                  # 模型目录
│   │   ├── config/                   # 配置
│   │   ├── errors/                   # 错误处理
│   │   ├── providers/                # 提供商
│   │   ├── request/                  # 请求构建
│   │   ├── response/                 # 响应处理
│   │   ├── streaming/                # 流式处理
│   │   └── structuredOutput/         # 结构化输出
│   ├── permission/                   # 权限系统
│   ├── pilot/                        # 配置管理
│   ├── router/                       # 智能路由
│   │   ├── config/                   # 配置
│   │   ├── customRouter/             # 自定义路由
│   │   ├── fallback/                 # 降级策略
│   │   ├── orchestrate/              # 编排
│   │   ├── protocol/                 # 协议
│   │   ├── retry/                    # 重试
│   │   ├── scenario/                 # 场景检测
│   │   ├── session/                  # 会话存储
│   │   ├── stats/                    # 统计
│   │   └── tokenSaver/               # Token优化
│   ├── session/                      # 会话管理
│   │   ├── filesystem/               # 文件系统存储
│   │   ├── metadata/                 # 元数据
│   │   ├── resume/                   # 会话恢复
│   │   ├── storage/                  # 存储抽象
│   │   ├── transcript/               # 对话记录
│   │   └── worktree/                 # 工作树管理
│   ├── task/                         # 任务管理
│   ├── tool/                         # 工具系统
│   │   ├── audit/                    # 审计记录
│   │   ├── builtin/                  # 内置工具
│   │   ├── elicitation/              # 引导工具
│   │   ├── execution/                # 执行引擎
│   │   ├── protocol/                 # 协议定义
│   │   ├── registry/                 # 工具注册
│   │   └── scheduler/                # 调度器
│   └── web/                          # Web相关
├── ui/                               # 前端界面
├── skills/                           # 技能库
├── products/                         # 产品配置示例
├── scripts/                          # 脚本工具
└── tests/                            # 测试用例
```

---

## 核心模块详解

### 1. Agent 层

Agent 层是 PilotDeck 的核心运行时，负责执行 AI 代理的主要逻辑。

#### 1.1 AgentLoop

**文件**: [src/agent/loop/AgentLoop.ts](file:///workspace/PilotDeck/src/agent/loop/AgentLoop.ts)

**职责**: 代理的核心循环控制器，管理对话轮次的执行流程。

**核心方法**:
- `run()`: 执行代理循环
- `snapshotFileState()`: 快照文件状态

**循环流程**:
1. 接收用户输入
2. 构建提示词
3. 调用模型
4. 解析工具调用
5. 执行工具
6. 收集结果
7. 决定是否继续循环

#### 1.2 TurnRunner

**文件**: [src/agent/turn/TurnRunner.ts](file:///workspace/PilotDeck/src/agent/turn/TurnRunner.ts)

**职责**: 单轮对话的执行器，协调输入处理、模型调用和结果记录。

**核心方法**:
- `run(options)`: 执行单轮对话
- `snapshotForRuntimeReload()`: 生成运行时重载快照

#### 1.3 AgentSession

**文件**: [src/agent/session/AgentSession.ts](file:///workspace/PilotDeck/src/agent/session/AgentSession.ts)

**职责**: 管理单个代理会话的状态和生命周期。

**核心方法**:
- `submitTurn()`: 提交对话轮次
- `close()`: 关闭会话
- `resume()`: 恢复会话

#### 1.4 createAgentSession

**文件**: [src/agent/session/createAgentSession.ts](file:///workspace/PilotDeck/src/agent/session/createAgentSession.ts)

**职责**: 会话工厂函数，负责创建完整的代理会话实例。

**核心配置项**:
```typescript
type CreateAgentSessionOptions = {
  sessionId: string;                    // 会话ID
  config: AgentRuntimeConfig;           // 运行时配置
  dependencies: AgentRuntimeDependencies; // 依赖注入
  transcript?: AgentTranscriptWriter;   // 对话记录器
  storage?: AgentProjectSessionStorage; // 会话存储
};
```

---

### 2. Gateway 层

**文件**: [src/gateway/Gateway.ts](file:///workspace/PilotDeck/src/gateway/Gateway.ts)

**职责**: 统一的网关服务，管理会话路由、事件分发和多渠道接入。

**核心组件**:

| 组件 | 职责 |
|------|------|
| `SessionRouter` | 会话路由和生命周期管理 |
| `InProcessGateway` | 进程内网关实现 |
| `RemoteGateway` | 远程网关客户端 |

**核心方法**:
- `createGateway(options)`: 创建网关实例
- `submitTurn(input)`: 提交对话轮次
- `listSessions()`: 列出会话
- `newSession(input)`: 创建新会话

---

### 3. Router 层

**文件**: [src/router/RouterRuntime.ts](file:///workspace/PilotDeck/src/router/RouterRuntime.ts)

**职责**: 智能路由系统，根据任务难度自动选择合适的模型，实现成本优化。

**核心特性**:

| 特性 | 描述 |
|------|------|
| **Token Saver** | 根据任务复杂度自动选择模型层级 |
| **智能降级** | 支持多级 fallback 策略 |
| **零使用重试** | 对空响应自动重试 |
| **瞬态重试** | 网络异常时自动重试 |
| **自动编排** | 支持主/子代理协同 |

**路由决策流程**:
```
用户请求 → 场景检测 → Token Saver 判断 → 模型选择 → 执行 → 结果返回
                                   ↓
                          缓存粘性决策
```

**核心方法**:
- `decide(input)`: 决定使用哪个模型
- `execute(decision, request)`: 执行模型调用
- `stream(request, ctx)`: 流式执行（decide + execute）
- `invalidateSticky(sessionId)`: 清除粘性路由

---

### 4. Model 层

**文件**: [src/model/ModelRuntime.ts](file:///workspace/PilotDeck/src/model/ModelRuntime.ts)

**职责**: 模型抽象层，统一管理不同模型提供商的调用。

**支持的提供商**:
- Anthropic (Claude)
- OpenAI (GPT)
- DeepSeek
- Qwen
- Kimi
- MiniMax

**核心方法**:
- `stream(request)`: 流式模型调用
- `complete(request)`: 完整模型调用
- `getCapabilities(providerId, modelId)`: 获取模型能力
- `getMultimodal(providerId, modelId)`: 获取多模态约束

---

### 5. Tool 层

**文件**: [src/tool/index.ts](file:///workspace/PilotDeck/src/tool/index.ts)

**职责**: 工具执行系统，提供代理可用的各种工具能力。

**内置工具分类**:

| 类别 | 工具名称 | 功能 |
|------|----------|------|
| 文件操作 | `readFile`, `writeFile`, `editFile` | 文件读写编辑 |
| 代码操作 | `bash`, `editNotebook` | 命令执行、笔记本编辑 |
| 搜索 | `glob`, `grep` | 文件匹配、内容搜索 |
| Web | `webFetch`, `webSearch` | 网页抓取、搜索 |
| 代理 | `agent` | 子代理调用 |
| 计划 | `planMode`, `todoWrite` | 计划模式、任务管理 |
| 结构化 | `structuredOutput` | 结构化输出 |

**核心组件**:
- `ToolRegistry`: 工具注册中心
- `ToolRuntime`: 工具执行运行时
- `ConcurrentToolScheduler`: 并发工具调度器

---

### 6. Context 层

**职责**: 上下文管理系统，处理内存、预算、压缩等核心功能。

#### 6.1 Memory 子系统

**文件**: [src/context/memory/EdgeClawMemoryProvider.ts](file:///workspace/PilotDeck/src/context/memory/EdgeClawMemoryProvider.ts)

**职责**: 白盒内存系统，支持记忆的存储、检索和编辑。

**核心方法**:
- `retrieve(input)`: 检索相关记忆
- `captureTurn(input)`: 捕获对话轮次到内存

**特点**:
- 可追溯: 记录每条记忆的来源和时间
- 可编辑: 支持直接编辑记忆条目
- WorkSpace 隔离: 每个项目有独立的内存空间
- 一键回滚: 支持恢复到之前的状态

#### 6.2 Budget 子系统

**文件**: [src/context/budget/TokenBudgetManager.ts](file:///workspace/PilotDeck/src/context/budget/TokenBudgetManager.ts)

**职责**: Token 预算管理，控制模型调用成本。

#### 6.3 Compaction 子系统

**文件**: [src/context/compaction/CompactionEngine.ts](file:///workspace/PilotDeck/src/context/compaction/CompactionEngine.ts)

**职责**: 消息压缩，减少上下文长度，降低 Token 消耗。

---

### 7. Extension 层

**文件**: [src/extension/index.ts](file:///workspace/PilotDeck/src/extension/index.ts)

**职责**: 扩展系统，支持插件、钩子和技能的动态加载。

**扩展类型**:

| 类型 | 描述 |
|------|------|
| **Plugins** | 插件系统，支持 MCP 服务器、工具、命令等 |
| **Hooks** | 生命周期钩子，可拦截关键事件 |
| **Skills** | 技能库，可复用的任务流程 |

**核心钩子事件**:
- `UserPromptSubmit`: 用户提示提交前
- `PreToolUse`: 工具使用前
- `PostToolUse`: 工具使用后
- `SessionEnd`: 会话结束时

---

### 8. Always-On 系统

**文件**: [src/always-on/index.ts](file:///workspace/PilotDeck/src/always-on/index.ts)

**职责**: 后台执行系统，支持任务的自动发现和执行。

**核心组件**:

| 组件 | 职责 |
|------|------|
| `AlwaysOnManager` | 后台执行管理器 |
| `DiscoveryScheduler` | 任务发现调度器 |
| `DiscoveryFire` | 发现执行引擎 |
| `WorkspaceProvider` | 工作空间提供者 |
| `ChannelLeaseRegistry` | 渠道租赁管理 |

**工作流程**:
1. **发现阶段**: 自动发现项目中待完成的任务
2. **计划阶段**: 生成执行计划
3. **执行阶段**: 后台执行任务
4. **报告阶段**: 生成完成报告

---

### 9. Cron 系统

**文件**: [src/cron/index.ts](file:///workspace/PilotDeck/src/cron/index.ts)

**职责**: 定时任务系统，支持 cron 表达式和一次性任务。

**核心方法**:
- `cronCreate()`: 创建定时任务
- `cronList()`: 列出任务
- `cronDelete()`: 删除任务
- `cronStop()`: 停止任务

---

### 10. Adapters 层

**文件**: [src/adapters/index.ts](file:///workspace/PilotDeck/src/adapters/index.ts)

**职责**: 多渠道适配器，支持多种消息平台接入。

**支持的渠道**:

| 渠道 | 类型 | 状态 |
|------|------|------|
| Feishu | 企业 IM | ✅ |
| Weixin | 微信 | ✅ |
| Discord | 社交 | ✅ |
| Slack | 企业 IM | ✅ |
| Telegram | 社交 | ✅ |
| QQ | 社交 | ✅ |
| DingTalk | 企业 IM | ✅ |
| WeCom | 企业微信 | ✅ |
| Email | 邮件 | ✅ |
| SMS | 短信 | ✅ |
| Webhook | Webhook | ✅ |
| API Server | API接口 | ✅ |
| CLI/TUI | 终端 | ✅ |

---

## 关键数据结构

### CanonicalMessage

```typescript
interface CanonicalMessage {
  role: "user" | "assistant" | "system" | "tool";
  content: Array<{
    type: "text" | "image" | "tool_result";
    text?: string;
    imageUrl?: string;
    toolResult?: ToolResult;
  }>;
  timestamp?: string;
}
```

### AgentLoopState

```typescript
interface AgentLoopState {
  messages: CanonicalMessage[];
  toolResults: ToolResult[];
  turns: number;
  usage: CanonicalUsage;
}
```

### RouterDecision

```typescript
interface RouterDecision {
  provider: string;           // 模型提供商
  model: string;              // 模型名称
  scenarioType: RouterScenarioType;
  tokenSaverTier?: string;    // Token Saver 层级
  isSubagent: boolean;        // 是否子代理
  orchestrating: boolean;     // 是否正在编排
  resolvedFrom: string;       // 决策来源
  mutations: RouterMutationsLog;
  requestPatch?: {
    messages?: CanonicalMessage[];
    tools?: ToolDefinition[];
    systemPrompt?: string;
  };
}
```

---

## 依赖关系

### 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| `@modelcontextprotocol/sdk` | ^1.29.0 | MCP 协议支持 |
| `js-tiktoken` | ^1.0.21 | Token 计数 |
| `yaml` | ^2.8.4 | YAML 解析 |
| `undici` | ^8.2.0 | HTTP 客户端 |
| `ws` | ^8.21.0 | WebSocket |
| `sharp` | ^0.34.5 | 图片处理 |
| `react` | ^19.2.6 | UI 框架 |
| `ink` | ^7.0.2 | CLI UI |

### 开发依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| `typescript` | ^5.9.3 | TypeScript |
| `tsx` | ^4.21.0 | TypeScript 运行 |
| `@types/node` | ^25.0.0 | Node 类型 |

---

## 项目运行

### 安装方式

**方式一：一键安装（推荐）**

```bash
curl -fsSL https://raw.githubusercontent.com/OpenBMB/PilotDeck/main/install.sh | bash
```

**方式二：源码安装**

```bash
git clone https://github.com/OpenBMB/PilotDeck.git
cd PilotDeck
npm install              # 安装根依赖
cd ui && npm install     # 安装 UI 依赖
cd ..
```

### 配置模型

创建配置文件 `~/.pilotdeck/pilotdeck.yaml`:

```yaml
schemaVersion: 1
agent:
  model: deepseek/deepseek-v4-pro
model:
  providers:
    deepseek:
      protocol: openai
      url: https://api.deepseek.com/v1
      apiKey: sk-your-api-key
```

### 启动服务

```bash
# 开发模式
cd ui && npm run dev     # 访问 http://localhost:5173

# 生产模式
cd ui && npm run start   # 访问 http://localhost:3001

# CLI 命令
pilotdeck server         # 启动服务器
pilotdeck tui            # 终端界面
pilotdeck skills migrate # 迁移技能
```

---

## 扩展开发

### 创建插件

插件是 PilotDeck 的主要扩展方式，通过 `plugin.json` 定义：

```json
{
  "name": "example-plugin",
  "version": "1.0.0",
  "contributions": {
    "tools": [
      {
        "name": "example-tool",
        "description": "示例工具",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": { "type": "string" }
          },
          "required": ["query"]
        }
      }
    ],
    "hooks": [
      {
        "event": "UserPromptSubmit",
        "handler": "./hooks/onPrompt.js"
      }
    ]
  }
}
```

### 创建钩子

钩子允许在关键事件点插入自定义逻辑：

```typescript
// hooks/onPrompt.js
export async function onPrompt(input) {
  console.log("User prompt received:", input.payload.prompt);
  
  // 返回钩子结果
  return {
    type: "sync",
    messages: [],
    effects: []
  };
}
```

---

## 架构设计原则

### 1. 模块化设计
- 每个模块职责单一，通过接口通信
- 依赖注入模式，便于测试和替换

### 2. 可扩展性
- 插件化架构，支持动态加载
- 钩子系统，支持拦截扩展

### 3. 可观测性
- 白盒内存，全程可追溯
- 详细的统计和日志

### 4. 高可用性
- 自动降级和重试机制
- 会话持久化和恢复

---

## 性能优化策略

### Token 优化
- 智能路由选择合适模型
- 消息压缩减少上下文长度
- 零使用检测避免无效调用

### 并发优化
- 工具并发执行
- 流式响应处理
- 缓存机制

### 资源管理
- 会话超时清理
- 内存限制控制
- 预算管理

---

## 安全考虑

### 权限控制
- 细粒度权限规则
- 工具白名单
- 网络请求白名单

### 输入验证
- 工具输入校验
- URL 安全验证
- 路径安全检查

### 审计日志
- 工具调用记录
- 权限决策记录
- 会话操作记录

---

## 总结

PilotDeck 是一个架构完善、功能丰富的 AI Agent 平台，核心优势包括：

1. **WorkSpace 隔离**: 项目级别的资源隔离，避免上下文污染
2. **白盒内存**: 可追溯、可编辑的内存系统
3. **智能路由**: 基于任务难度的模型选择，大幅降低成本
4. **始终在线**: 后台任务发现和执行能力
5. **多渠道支持**: 统一的渠道适配器架构
6. **开放扩展**: 插件化设计，易于扩展功能

该项目适合构建企业级 AI 助手、自动化工作流和智能生产力工具。