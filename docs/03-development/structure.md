# 项目结构说明

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 目录结构

```
devteam-ai/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/               # API 路由
│   │   ├── core/              # 核心配置
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务服务
│   │   └── main.py            # 应用入口
│   ├── tests/                 # 测试代码
│   └── data/                  # 数据文件
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── lib/               # 工具库
│   │   ├── pages/             # 页面组件
│   │   └── types/             # TypeScript 类型
│   └── index.html
│
├── docs/                       # 文档系统
│   ├── 01-project/            # 项目概览
│   ├── 02-design/             # 设计文档
│   ├── 03-development/        # 开发指南
│   ├── 04-modules/            # 模块文档
│   ├── 05-api/                # API 文档
│   ├── 06-roadmap/            # 路线图
│   ├── 07-research/           # 调研文档
│   ├── 08-process/            # 过程文档
│   ├── 09-specs/              # 规格文档
│   └── 10-contributing/       # 贡献指南
│
└── scripts/                    # 脚本工具
```

---

## 后端模块

| 目录 | 说明 |
|------|------|
| `app/api/` | REST API 路由定义 |
| `app/core/` | 核心配置和 LLM 适配 |
| `app/models/` | 数据库模型定义 |
| `app/services/` | 业务逻辑服务 |

---

## 前端模块

| 目录 | 说明 |
|------|------|
| `src/components/` | React 组件 |
| `src/lib/` | API 客户端和状态管理 |
| `src/pages/` | 页面组件 |
| `src/types/` | TypeScript 类型定义 |

---

## 相关文档

- [环境搭建](./setup.md)
- [模块文档](../04-modules/)
