# 装备服务模块

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：Agent 装备管理
- **所属层级**：backend
- **代码路径**：`backend/app/services/equipment/`

---

## 功能特性

- 装备注册和管理
- 装备分配给 Agent
- 装备使用追踪

---

## 核心组件

### GearManager

装备管理器。

| 方法 | 说明 |
|------|------|
| `register_gear()` | 注册装备 |
| `assign_gear()` | 分配装备 |
| `list_gears()` | 列出装备 |

---

## 依赖关系

- 依赖：数据库
- 被依赖：Agent 服务

---

## 相关文档

- [Gear 模型](./models/gear.md)
