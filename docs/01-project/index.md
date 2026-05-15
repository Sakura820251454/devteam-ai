# 项目概览

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 文档分类导航

本项目的文档系统按照软件工程最佳实践组织，共分为 10 个分类：

| 编号 | 分类 | 说明 | 链接 |
|------|------|------|------|
| 01 | 项目概览 | 项目愿景、架构、原则 | 当前目录 |
| 02 | 设计文档 | 产品设计、核心概念 | [02-design](../02-design/) |
| 03 | 开发指南 | 环境搭建、编码规范 | [03-development](../03-development/) |
| 04 | 模块文档 | 代码模块文档（一一对应） | [04-modules](../04-modules/) |
| 05 | API 文档 | 接口文档 | [05-api](../05-api/) |
| 06 | 路线图 | 开发规划 | [06-roadmap](../06-roadmap/) |
| 07 | 贡献指南 | 如何贡献 | [07-contributing](../07-contributing/) |

---

## 快速开始

### 新成员入门

1. 阅读 [项目愿景](./vision.md) 了解项目目标
2. 阅读 [系统架构](./architecture.md) 了解整体设计
3. 阅读 [设计原则](./principles.md) 了解开发规范
4. 查看 [开发指南](../03-development/) 开始开发

### 开发者入门

1. 阅读 [环境搭建](../03-development/setup.md) 配置开发环境
2. 阅读 [项目结构](../03-development/structure.md) 了解代码组织
3. 查看 [模块文档](../04-modules/) 了解各模块功能

---

## 文档约定

### 命名规范

- **目录命名**: `两位数字-小写英文`，如 `01-project`, `02-design`
- **文件命名**: `小写英文-连字符`，如 `agent-service.md`, `memory-system.md`
- **ADR 命名**: `YYYY-MM-DD-标题.md`

### 代码-文档映射

每个代码模块都有对应的文档，位于 `04-modules/` 目录下：

```
backend/app/services/agent/ → 04-modules/backend/agent-service.md
frontend/src/components/CollaborationView.tsx → 04-modules/frontend/collaboration-view.md
```

---

## 相关链接

- [术语表](./glossary.md)
- [变更日志](./changelog.md)
