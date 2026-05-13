---
layout: home

hero:
  name: "DevTeam-AI"
  text: "多 Agent 协作开发平台"
  tagline: 模拟真实软件开发团队的协作模式
  actions:
    - theme: brand
      text: 快速开始
      link: /01-project/
    - theme: alt
      text: 设计文档
      link: /02-design/
    - theme: alt
      text: GitHub
      link: https://github.com/your-org/devteam-ai

features:
  - icon: 🤖
    title: Agent 人才库
    details: 每个 Agent 都是具有独特个性的个体，通过 soul.md 定义行为准则
  - icon: 🧠
    title: 分层记忆系统
    details: L1-L4 四层记忆架构，实现高效的信息存储和检索
  - icon: 📋
    title: 任务看板
    details: 可视化任务管理，支持拖拽操作和实时状态更新
  - icon: 🔄
    title: 团队协作
    details: 多 Agent 并行协作，支持公共讨论和私聊
  - icon: ⚡
    title: 人类干预
    details: 实时干预机制，随时调整任务执行
  - icon: 📈
    title: 自我学习
    details: 知识沉淀与技能积累，系统越用越智能
---

## 文档导航

| 分类 | 说明 | 链接 |
|------|------|------|
| 01-项目 | 项目愿景、架构、原则 | [开始阅读](/01-project/) |
| 02-设计 | 产品设计、核心概念 | [开始阅读](/02-design/) |
| 03-开发 | 环境搭建、编码规范 | [开始阅读](/03-development/) |
| 04-模块 | 代码模块文档 | [开始阅读](/04-modules/) |
| 05-API | 接口文档 | [开始阅读](/05-api/) |
| 06-路线图 | 开发规划 | [开始阅读](/06-roadmap/) |

## 代码-文档映射

每个代码模块都有对应的文档，位于 `04-modules/` 目录：

```
backend/app/services/agent/ → 04-modules/backend/agent-service.md
frontend/src/components/CollaborationView.tsx → 04-modules/frontend/collaboration-view.md
```

## 快速开始

```bash
# 克隆项目
git clone https://github.com/your-org/devteam-ai.git
cd devteam-ai

# 后端环境
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# 前端环境
cd frontend
npm install
npm run dev
```
