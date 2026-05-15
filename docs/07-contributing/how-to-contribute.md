# 如何贡献

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 贡献流程

### 1. Fork 项目

在 GitHub 上 Fork 项目到你的账户。

### 2. 克隆仓库

```bash
git clone https://github.com/your-username/devteam-ai.git
cd devteam-ai
```

### 3. 创建分支

```bash
git checkout -b feature/your-feature-name
```

### 4. 进行开发

- 遵循编码规范
- 编写测试
- **更新文档**（新增/修改代码模块时必须同步更新对应文档）

#### 文档更新规则

| 代码变更 | 需要更新的文档 |
|----------|--------------|
| 新增/修改 Service（`backend/app/services/`） | `docs/04-modules/backend/` 对应模块文档 |
| 新增/修改 API 路由（`backend/app/api/`） | `docs/05-api/` 对应 API 文档 |
| 新增/修改数据模型（`backend/app/models/`） | `docs/04-modules/backend/models/` 对应模型文档 |
| 新增/修改前端组件 | `docs/04-modules/frontend/` 对应组件文档 |
| 新增/修改 `doc_sync_config.json` 映射 | 确保新代码文件有对应的文档映射 |

#### 文档同步检查

提交前运行文档同步检查：

```bash
# 检查代码变更是否有关联文档更新
python scripts/doc_sync.py --check

# 查看所有代码-文档映射
python scripts/doc_sync.py --list
```

CI 会自动运行此检查，未通过则构建失败。

### 5. 提交变更

```bash
git add .
git commit -m "feat: 添加新功能"
```

### 6. 推送分支

```bash
git push origin feature/your-feature-name
```

### 7. 创建 Pull Request

在 GitHub 上创建 Pull Request，描述你的变更。

---

## 提交信息规范

使用 Conventional Commits：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关

---

## 相关文档

- [编码规范](../03-development/coding-standards.md)
- [文档风格指南](./doc-style-guide.md)
