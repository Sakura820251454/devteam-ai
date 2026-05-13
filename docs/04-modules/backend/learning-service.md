# 学习服务模块

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：自我学习机制
- **所属层级**：backend
- **代码路径**：`backend/app/services/learning/`

---

## 功能特性

- 知识提取
- 技能沉淀
- 轨迹记录
- 经验匹配

---

## 核心组件

### SkillManager

技能管理器。

| 方法 | 说明 |
|------|------|
| `create_skill()` | 创建技能 |
| `get_skill()` | 获取技能 |
| `list_skills()` | 列出技能 |

### TrajectoryRecorder

轨迹记录器。

| 方法 | 说明 |
|------|------|
| `record()` | 记录轨迹 |
| `get_trajectory()` | 获取轨迹 |

---

## 依赖关系

- 依赖：知识服务、记忆服务
- 被依赖：Agent 服务

---

## 相关文档

- [自我学习设计](../../02-design/self-learning.md)
- [记忆系统设计](../../02-design/memory-system.md)
