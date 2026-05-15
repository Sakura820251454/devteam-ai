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
    details: 无预设角色，任务驱动临时职责。每个 Agent 通过 soul.md 定义性格、沟通风格、决策偏好和风险倾向四维个性。固定统筹 Agent 主导协作，团队风格在任务-复盘循环中自然形成
  - icon: 🧠
    title: 分层记忆系统
    details: L1/L2/L3 三层私有记忆 + 独立共享向量存储。参考 CrewAI Cognitive Memory 模型，框架自动管理记忆编码、合并、检索、提取和遗忘。跨 Agent 知识共享需经讨论或统筹决策
  - icon: 📋
    title: 任务调度流水线
    details: 需求分析 → 任务拆解 → DAG 并行执行 → Agent 互审 → 用户验收。统筹 Agent 决策分配，多维风险评级，灰盒模型让用户只需关注任务输入和结果验收
  - icon: 🔄
    title: 多 Agent 协作
    details: 统筹 Agent 主持讨论、控制发言权，Agent 可举手请求发言。全员可见公共讨论，分歧先互相说服再上报用户裁决，机制上设定辩论轮次上限防止 Token 爆炸
  - icon: ⚡
    title: 人类干预
    details: 用户可随时主动介入，聊天框自然语言 + 一个停止按钮。支持单 Agent 粒度暂停/重做，仅覆盖三个核心场景：纠错暂停、结果驳回重做、需求变更
  - icon: 📈
    title: 自我学习与进化
    details: 大任务验收后触发复盘，产出三条路径：流程最佳实践生成 SKILL.md、个体问题优化 soul（需用户确认）、技术知识沉淀共享向量库。用户介入统计反馈形成执行准则
---

## 文档导航

| 分类 | 说明 | 链接 |
|------|------|------|
| 01-项目 | 项目愿景、架构、原则 | [开始阅读](/01-project/) |
| 02-设计 | 产品设计、核心概念 | [开始阅读](/02-design/) |
| 03-开发 | 环境搭建、编码规范 | [开始阅读](/03-development/) |
| 04-模块 | 代码模块文档（15 个后端服务 + 5 个前端组件） | [开始阅读](/04-modules/) |
| 05-API | 接口文档（15 个 API 模块） | [开始阅读](/05-api/) |
| 06-路线图 | 开发规划 | [开始阅读](/06-roadmap/) |
| 07-贡献 | 贡献指南和规范 | [开始阅读](/07-contributing/) |

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
