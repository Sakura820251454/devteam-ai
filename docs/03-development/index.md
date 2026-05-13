# 开发指南

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 概述

本目录包含 DevTeam-AI 的开发指南，帮助开发者快速上手和规范开发。

---

## 文档列表

| 文档 | 说明 |
|------|------|
| [环境搭建](./setup.md) | 开发环境配置指南 |
| [项目结构](./structure.md) | 项目目录结构说明 |
| [编码规范](./coding-standards.md) | 代码风格和规范 |
| [API 开发规范](./api-guidelines.md) | API 接口开发规范 |
| [测试指南](./testing.md) | 测试编写指南 |

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd devteam-ai

# 后端环境
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 前端环境
cd ../frontend
npm install
```

### 2. 启动服务

```bash
# 启动后端
cd backend
python -m uvicorn app.main:app --reload

# 启动前端
cd frontend
npm run dev
```

---

## 相关文档

- [项目愿景](../01-project/vision.md)
- [系统架构](../01-project/architecture.md)
- [模块文档](../04-modules/)
