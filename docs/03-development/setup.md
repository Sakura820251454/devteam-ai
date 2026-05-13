# 环境搭建指南

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 1. 系统要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.11+ |
| Node.js | 18+ |
| SQLite | 3.x |

---

## 2. 后端环境

### 2.1 创建虚拟环境

```bash
cd backend
python -m venv venv
```

### 2.2 激活虚拟环境

```bash
# Linux/Mac
source venv/bin/activate

# Windows
.\venv\Scripts\activate
```

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

### 2.4 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

---

## 3. 前端环境

### 3.1 安装依赖

```bash
cd frontend
npm install
```

### 3.2 启动开发服务器

```bash
npm run dev
```

---

## 4. 验证安装

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

---

## 相关文档

- [项目结构](./structure.md)
- [编码规范](./coding-standards.md)
