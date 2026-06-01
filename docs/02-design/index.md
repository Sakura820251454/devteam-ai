# 设计文档

**最后更新**: 2026-05-29

---

## 概述

本目录包含 DevTeam-AI 的核心设计文档，描述系统是什么、为什么这样设计。

---

## 核心概念

| 文档 | 说明 |
|------|------|
| [任务执行流程](./execution-flow.md) | 从任务输入到交付总结的完整流程 |
| [Agent 模型](./agent-model.md) | Agent 人才库模式设计 |
| [记忆系统](./memory-system.md) | 分层记忆系统设计 |
| [任务模型](./task-model.md) | 任务生命周期管理 |
| [通信机制](./communication.md) | Agent 间通信设计 |

## 功能特性

| 文档 | 说明 |
|------|------|
| [团队协作](./collaboration.md) | 多 Agent 协作设计 |
| [任务看板](./task-board.md) | 任务看板设计 |
| [干预系统](./intervention.md) | 人类干预机制 |
| [自我学习](./self-learning.md) | 知识沉淀与进化 |
| [Prompt 架构](./prompt-architecture.md) | Prompt Registry 统一管理设计 |

## 架构决策记录 (ADR)

| 编号 | 标题 | 状态 |
|------|------|------|
| [ADR-001](./decisions/2026-05-13-vitepress-decision.md) | 选择 VitePress 作为文档系统 | 已接受 |

更多 ADR 见 [决策记录索引](./decisions/index.md)。

## 过程文档

技术调研、设计决策等过程文档存放在 [process/](../process/) 目录。

---

## 相关文档

- [项目愿景](../01-project/vision.md)
- [系统架构](../01-project/architecture.md)
