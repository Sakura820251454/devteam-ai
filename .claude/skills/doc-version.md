# doc-version

管理版本号和变更日志。

## 触发方式

- 用户输入 `/doc-version`

## 版本号规则

### 版本格式

`vX.Y.Z`（如 v3.1.2）

| 位置 | 名称 | 含义 |
|------|------|------|
| X | MAJOR | 重大架构变更或不兼容的 API 修改 |
| Y | MINOR | 新功能、新模块、向下兼容的功能性新增 |
| Z | PATCH | Bug 修复、文档修正、向下兼容的问题修正 |

### 升级判断标准

**MAJOR（X+1，Y/Z 归零）**：
- 删除或重命名公共 API 端点
- 数据库 schema 不兼容变更
- 配置格式变更导致旧配置无法使用
- 整体架构重构（如从 REST 改为 GraphQL）

**MINOR（Y+1，Z 归零）**：
- 新增 API 端点
- 新增服务模块或功能
- 新增 Agent 能力（装备、工具、技能）
- 新增前端页面或组件
- Pipeline 新增阶段模板

**PATCH（Z+1）**：
- Bug 修复
- 文档更新（不涉及功能变更）
- 代码重构（不改变外部行为）
- 测试补充
- 依赖版本更新

### 特殊情况

| 场景 | 版本变更 |
|------|---------|
| 只改了文档 | PATCH |
| 只改了测试 | 不升版本 |
| 改了 Prompt 模板 | PATCH（除非新增了模板类型） |
| 改了 Agent soul.md | PATCH（除非新增了 Agent） |

## 执行步骤

1. **确定版本号**
   - 运行 `git diff --stat HEAD~5` 查看最近变更
   - 根据上述规则自动判断应该升 major/minor/patch
   - 读取 `docs/01-project/changelog.md` 获取当前版本号
   - 计算新版本号

2. **收集变更内容**
   - 运行 `git diff` 查看具体变更
   - 按模块分类：
     - 后端变更（backend/）
     - 前端变更（frontend/）
     - 文档变更（docs/）
     - 其他变更

3. **生成 changelog 条目**
   ```markdown
   ## [vX.Y.Z] - YYYY-MM-DD

   ### 变更类别

   **后端**：
   - 变更描述

   **前端**：
   - 变更描述

   **文档**：
   - 变更描述
   ```

4. **更新文件**
   - 更新 `docs/01-project/changelog.md` 头部版本号和日期
   - 在 changelog 中添加新版本条目

5. **输出更新结果**
   ```
   [DOC VERSION] 版本更新 v3.0.0 → v3.1.0：
   - 变更类型: MINOR（新增功能）
   - docs/01-project/changelog.md 已更新
   - 新增 8 条变更记录
   ```

## 版本号存储位置

版本号在以下位置维护：

| 位置 | 用途 |
|------|------|
| `docs/01-project/changelog.md` 头部 | 主版本号（权威来源） |
| `docs/01-project/changelog.md` 各条目 | 历史版本记录 |
| 其他文档头部 | 反映该文档最后同步的版本 |

**规则**：`changelog.md` 头部是版本号的唯一权威来源。其他文档的版本号表示"最后同步到哪个版本"，不需要每次手动更新——运行 `/doc-sync` 时会自动更新。
