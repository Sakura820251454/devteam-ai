# 编码规范

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 1. Python 规范

### 1.1 代码风格

- 遵循 PEP 8 规范
- 使用 Black 格式化代码
- 使用 isort 排序导入

### 1.2 类型注解

```python
def process_task(task_id: str) -> dict[str, Any]:
    """处理任务"""
    pass
```

### 1.3 文档字符串

```python
def create_agent(name: str, role: str) -> Agent:
    """
    创建新的 Agent。
    
    Args:
        name: Agent 名称
        role: Agent 角色
        
    Returns:
        创建的 Agent 实例
    """
    pass
```

---

## 2. TypeScript 规范

### 2.1 代码风格

- 使用 ESLint 检查代码
- 使用 Prettier 格式化代码

### 2.2 类型定义

```typescript
interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'executing' | 'completed';
}
```

### 2.3 组件命名

- 组件文件使用 PascalCase：`AgentCard.tsx`
- 工具函数使用 camelCase：`formatDate.ts`

---

## 3. 提交规范

使用 Conventional Commits 规范：

```
feat: 添加新功能
fix: 修复 bug
docs: 文档更新
refactor: 代码重构
test: 测试相关
```

---

## 相关文档

- [API 开发规范](./api-guidelines.md)
- [测试指南](./testing.md)
