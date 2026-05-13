# 知识服务模块

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：知识库管理
- **所属层级**：backend
- **代码路径**：`backend/app/services/knowledge/`

---

## 功能特性

- 知识条目管理
- 知识检索
- 知识分类

---

## 核心组件

### KnowledgeService

知识管理的主要服务类。

| 方法 | 说明 |
|------|------|
| `add_knowledge()` | 添加知识 |
| `search_knowledge()` | 搜索知识 |
| `delete_knowledge()` | 删除知识 |

---

## 依赖关系

- 依赖：向量存储
- 被依赖：学习服务

---

## 相关文档

- [自我学习设计](../../02-design/self-learning.md)
