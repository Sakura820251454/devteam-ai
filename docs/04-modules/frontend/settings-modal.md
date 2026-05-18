# 系统设置弹窗

**版本**: v1.0
**最后更新**: 2026-05-18

---

## 概述

- **功能定位**：用户通过前端界面配置系统参数，无需编辑配置文件
- **代码路径**：`frontend/src/components/SettingsModal.tsx`

---

## 功能特性

- 显示当前工作区存储路径（配置值 + 解析后的绝对路径）
- 修改工作区路径（支持相对路径和绝对路径）
- 显示已有项目统计
- 修改后自动持久化到后端 `data/settings.json`
- 通过顶栏 ⚙ 图标打开

---

## 数据流

```
SettingsModal ⚙
  → GET /api/settings → 读取当前设置
  → 用户修改 workspace_root → 点击保存
  → PATCH /api/settings → 写入 data/settings.json
  → onSettingsChanged 回调 → 更新 store.workspacePath
  → 下次创建项目使用新路径
```

---

## Props

| 属性 | 类型 | 说明 |
|------|------|------|
| `isOpen` | boolean | 是否显示 |
| `onClose` | () => void | 关闭回调 |
| `onSettingsChanged` | (workspaceRoot: string) => void | 路径变更回调 |

---

## 相关文档

- [Settings API](../../05-api/settings.md)
- [Workspaces API](../../05-api/workspaces.md)
