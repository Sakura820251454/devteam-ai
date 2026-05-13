# DevTeam-AI 多智能体协同开发系统

Multi-agent collaborative development platform for AI-powered software development teams.

## 📋 项目概述

DevTeam-AI 是一个多智能体协同开发平台，旨在模拟真实软件开发团队的协作模式。通过构建具有差异化能力、性格和专业领域的 AI Agent 团队，实现高效的任务协作、实时的人类干预、系统的知识沉淀以及持续的能力进化。

## 🛠️ 技术栈

- **后端**: Python 3.11+ / FastAPI
- **前端**: React 18 / TypeScript / Tailwind CSS / Vite
- **数据库**: SQLite (开发) → PostgreSQL (生产)
- **LLM**: DeepSeek (国产低成本高性能模型)

## 🚀 快速开始

### 1. 环境准备

```bash
# Python 3.11+
python --version

# Node.js 18+
node --version
```

### 2. 后端设置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 DeepSeek API Key
```

### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install
```

### 4. 启动服务

```bash
# 启动后端 (在 backend 目录)
uvicorn app.main:app --reload --port 8000

# 启动前端 (在 frontend 目录，新终端)
npm run dev
```

### 5. 访问应用

打开浏览器访问 http://localhost:3000

## ✨ Phase 1 功能

✅ 初始化 Agent（带有个性化配置）  
✅ 创建对话会话  
✅ 与 Agent 进行流式对话  
✅ 消息历史记录  
✅ Token 使用统计  
✅ Agent 人才库模式  
✅ 分层记忆系统  
✅ 任务制分配机制  

## 📂 项目结构

```
devteam-ai/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── core/         # 核心配置
│   │   ├── models/       # 数据模型
│   │   ├── services/     # 业务服务
│   │   └── main.py       # 应用入口
│   ├── agents/           # Agent 人才库（soul.md 文件）
│   ├── tests/            # 单元测试
│   ├── pyproject.toml    # Python 项目配置
│   └── .env.example      # 环境变量示例
│
├── frontend/
│   ├── src/
│   │   ├── api/          # API 调用
│   │   ├── components/   # React 组件
│   │   ├── hooks/        # 自定义 Hooks
│   │   ├── lib/          # 工具库
│   │   └── pages/        # 页面
│   ├── package.json
│   └── vite.config.ts
│
└── docs/                  # 文档中心
    ├── README.md          # 文档入口
    ├── CONTRIBUTING.md    # 贡献指南
    ├── design/            # 设计文档
    │   ├── 01-overview/   # 系统概述
    │   ├── 02-core-concepts/  # 核心概念
    │   ├── 03-features/   # 功能设计
    │   └── 04-roadmap/    # 路线图
    └── development/       # 开发文档
        ├── 01-setup/      # 环境搭建
        ├── 02-backend/    # 后端开发
        ├── 03-frontend/   # 前端开发
        ├── 04-testing/    # 测试
        └── 05-deployment/ # 部署
```

## 📚 文档中心

项目文档分为两大类：

| 文档类型 | 路径 | 用途 |
|---------|------|------|
| **设计文档** | `docs/design/` | 回答「为什么」和「是什么」，面向产品经理和架构师 |
| **开发文档** | `docs/development/` | 回答「怎么做」，面向开发者 |

详细文档请访问：[docs/README.md](docs/README.md)

## 📡 API 文档

启动后端服务后，访问以下地址查看 API 文档：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🗺️ 开发计划

- [x] **Phase 1**: 核心骨架 (Week 1-2) - 已完成
- [x] **Phase 2**: 协作引擎 (Week 3-4) - 已完成
- [x] **Phase 3**: 干预系统 (Week 5-6) - 已完成
- [ ] **Phase 4**: 文档与记忆 (Week 7-8) - 进行中
- [ ] **Phase 5**: 智能装备与进化 (Week 9-10)
- [ ] **Phase 6**: 优化与整合 (Week 11-12)

## 🤝 贡献指南

欢迎贡献代码和文档！请阅读 [贡献指南](docs/CONTRIBUTING.md)。

## 📝 License

MIT

---

**版本**: v1.0  
**最后更新**: 2026-05-11  
**维护者**: DevTeam-AI 团队
