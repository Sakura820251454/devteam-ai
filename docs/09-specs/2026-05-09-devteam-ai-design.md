# DevTeam-AI 设计规格

**版本**: v2.0  
**日期**: 2026-05-09  
**状态**: 正式版

---

## 1. 项目概述

DevTeam-AI 是一个多智能体协同开发平台，模拟真实软件开发团队的协作模式。

---

## 2. 核心组件

### 2.1 Agent 系统

- Agent 人才库模式
- Soul 文件定义
- 独立上下文

### 2.2 记忆系统

- L1 工作记忆
- L2 短期记忆
- L3 长期记忆
- L4 向量检索

### 2.3 任务系统

- 任务生命周期
- 任务分配
- 任务执行

---

## 3. 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python/FastAPI |
| 前端 | React/TypeScript |
| 数据库 | SQLite |
| LLM | DeepSeek |
| 向量检索 | FAISS |

---

## 相关文档

- [项目愿景](../01-project/vision.md)
- [系统架构](../01-project/architecture.md)
