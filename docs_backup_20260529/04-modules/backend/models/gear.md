# Gear 模型

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：装备数据结构定义
- **代码路径**：`backend/app/models/gear_db.py`

---

## 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 装备唯一标识 |
| `name` | string | 装备名称 |
| `type` | string | 装备类型 |
| `config` | json | 装备配置 |
| `created_at` | datetime | 创建时间 |

---

## 相关文档

- [装备服务](../equipment-service.md)
