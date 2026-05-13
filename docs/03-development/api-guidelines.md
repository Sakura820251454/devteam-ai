# API 开发规范

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 1. 路由设计

### 1.1 URL 规范

- 使用复数名词：`/api/agents`, `/api/tasks`
- 使用连字符分隔：`/api/task-assignments`
- 避免嵌套过深：最多 2 层

### 1.2 HTTP 方法

| 方法 | 用途 |
|------|------|
| GET | 获取资源 |
| POST | 创建资源 |
| PUT | 更新资源 |
| DELETE | 删除资源 |

---

## 2. 响应格式

### 2.1 成功响应

```json
{
  "status": "success",
  "data": { ... },
  "message": "操作成功"
}
```

### 2.2 错误响应

```json
{
  "status": "error",
  "data": null,
  "message": "错误描述",
  "error_code": "ERR_001"
}
```

---

## 3. 错误码规范

| 错误码 | 说明 |
|--------|------|
| ERR_001 | 参数验证失败 |
| ERR_002 | 资源不存在 |
| ERR_003 | 权限不足 |
| ERR_004 | 内部错误 |

---

## 相关文档

- [API 文档](../05-api/)
- [编码规范](./coding-standards.md)
