# 项目结构说明

**版本**: v3.0  
**最后更新**: 2026-05-29

---

## 目录结构

```
devteam-ai/
├── backend/                        # 后端代码
│   ├── app/
│   │   ├── api/                   # API 路由
│   │   ├── core/                  # 核心配置（Settings、LLM 适配）
│   │   ├── database/              # 数据库连接和迁移
│   │   ├── models/                # SQLAlchemy 数据模型
│   │   ├── prompts/               # Prompt 模板文件
│   │   ├── services/              # 业务逻辑服务
│   │   └── main.py                # FastAPI 应用入口
│   ├── agents/                    # Agent 人才库
│   │   ├── agent_xiaowang/        # 每个 Agent 一个目录
│   │   │   ├── soul.md            # Agent 人格设定
│   │   │   └── growth.json        # 成长记录
│   │   └── ...                    # 更多 Agent
│   ├── tests/                     # 测试代码
│   │   ├── unit/                  # 单元测试
│   │   ├── integration/           # 集成测试
│   │   ├── e2e/                   # 端到端测试
│   │   ├── scenarios/             # 场景测试
│   │   └── mock/                  # 测试辅助
│   └── data/                      # 运行时数据
│       ├── audit/                 # 审计日志（audit.jsonl）
│       └── vector_index/          # FAISS 向量索引
│
├── frontend/                       # 前端代码
│   ├── src/
│   │   ├── components/            # React 组件
│   │   ├── hooks/                 # 自定义 Hooks
│   │   ├── lib/                   # API 客户端和工具函数
│   │   ├── pages/                 # 页面组件
│   │   ├── test/                  # 测试辅助
│   │   └── types/                 # TypeScript 类型定义
│   └── index.html
│
├── docs/                           # 文档系统（AI 项目记忆）
│   ├── 01-project/                # 项目概览（vision、architecture）
│   ├── 02-design/                 # 设计文档（任务、协作、记忆、学习）
│   ├── 03-development/            # 开发指南（setup、structure）
│   ├── 04-modules/                # 模块文档（backend、frontend）
│   ├── 05-api/                    # API 文档
│   ├── 06-roadmap/                # 路线图
│   ├── 07-contributing/           # 贡献指南
│   ├── 08-tracker/                # 差异追踪（doc-code 一致性）
│   └── process/                   # 过程文档（设计决策、调研、变更记录）
│
└── scripts/                        # 脚本工具
```

---

## 后端模块

| 目录 | 说明 |
|------|------|
| `app/api/` | REST API 路由定义 |
| `app/core/` | 核心配置（Settings、LLM 适配） |
| `app/database/` | 数据库连接和迁移 |
| `app/models/` | SQLAlchemy 数据模型定义 |
| `app/prompts/` | Prompt 模板文件 |
| `app/services/` | 业务逻辑服务（collaboration、equipment、knowledge、memory、project） |
| `agents/` | Agent 人才库（soul.md + growth.json） |
| `tests/unit/` | 单元测试 |
| `tests/integration/` | 集成测试 |
| `tests/e2e/` | 端到端测试 |
| `tests/scenarios/` | 场景测试 |
| `data/audit/` | 审计日志 |
| `data/vector_index/` | FAISS 向量索引 |

---

## 前端模块

| 目录 | 说明 |
|------|------|
| `src/components/` | React 组件 |
| `src/hooks/` | 自定义 Hooks |
| `src/lib/` | API 客户端和工具函数 |
| `src/pages/` | 页面组件 |
| `src/test/` | 测试辅助 |
| `src/types/` | TypeScript 类型定义 |

---

## 相关文档

- [环境搭建](./setup.md)
- [模块文档](../04-modules/)
