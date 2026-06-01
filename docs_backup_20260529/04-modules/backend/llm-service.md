# LLM 服务模块

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：LLM 适配和调用
- **所属层级**：backend
- **代码路径**：`backend/app/services/llm/`

---

## 功能特性

- 多模型适配 (DeepSeek, GLM, Qwen)
- 成本追踪
- 智能路由
- 批量处理

---

## 核心组件

### LLMService

LLM 调用的主要服务类。

| 方法 | 说明 |
|------|------|
| `chat()` | 对话调用 |
| `complete()` | 文本补全 |
| `embed()` | 向量嵌入 |

### CostTracker

API 成本追踪。

| 方法 | 说明 |
|------|------|
| `track()` | 记录成本 |
| `get_stats()` | 获取统计 |

---

## 依赖关系

- 依赖：外部 LLM API
- 被依赖：Agent 服务

---

## 相关文档

- [系统架构](../../01-project/architecture.md)
