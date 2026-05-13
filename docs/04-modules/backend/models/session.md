# 会话模型

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

- **功能定位**：会话数据结构定义
- **代码路径**：`backend/app/models/session.py`

---

## 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 会话唯一标识 |
| `title` | string | 会话标题 |
| `status` | enum | 会话状态 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

---

## 相关文档

- [Session API](../../../05-api/sessions.md)
