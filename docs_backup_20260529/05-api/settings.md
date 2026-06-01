# Settings API

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

系统设置管理接口。数据持久化到 `backend/data/settings.json`。首次启动时从 `.env` 读取默认值，用户修改后保存到 JSON 文件。

---

## 接口列表

### 获取设置

| 属性 | 值 |
|------|-----|
| **Method** | GET |
| **Path** | `/api/settings` |

**Response:**
```json
{
  "workspace_root": "../../devteam-workspaces",
  "workspace_root_resolved": "D:/AIproject/devteam-workspaces"
}
```

- `workspace_root`：当前配置的值（可能是相对路径）
- `workspace_root_resolved`：解析后的绝对路径

---

### 更新设置

| 属性 | 值 |
|------|-----|
| **Method** | PATCH |
| **Path** | `/api/settings` |

**Request Body:**
```json
{
  "workspace_root": "D:/MyProjects/ai-output"
}
```

更新 `workspace_root` 并保存到 `data/settings.json`。支持相对路径（相对于 `backend/` 目录）和绝对路径。

---

## 持久化机制

```
首次启动 → 读取 .env (Settings.workspace_root)
         → GET /api/settings 返回此默认值
         
用户修改 → PATCH /api/settings 
        → 写入 data/settings.json
        → workspace_manager 自动读取新路径
        → 后续项目创建使用新路径

重启后   → data/settings.json 存在 → 使用其中的值
         → data/settings.json 不存在 → 回退到 .env 默认值
```

---

## 相关文档

- [Workspaces API](./workspaces.md)
- [项目管理服务](../04-modules/backend/project-service.md)
