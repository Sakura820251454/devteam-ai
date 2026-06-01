# 测试指南

**版本**: v2.0  
**最后更新**: 2026-05-13

---

## 1. 测试类型

| 类型 | 目录 | 说明 |
|------|------|------|
| 单元测试 | `tests/unit/` | 测试单个函数或类 |
| 集成测试 | `tests/integration/` | 测试模块间交互 |
| E2E 测试 | `tests/e2e/` | 端到端测试 |

---

## 2. 测试规范

### 2.1 测试命名

```python
def test_create_agent_success():
    """测试创建 Agent 成功"""
    pass

def test_create_agent_with_invalid_name():
    """测试使用无效名称创建 Agent"""
    pass
```

### 2.2 测试结构

```python
def test_example():
    # Arrange - 准备测试数据
    agent_data = {"name": "test"}
    
    # Act - 执行测试操作
    result = create_agent(agent_data)
    
    # Assert - 验证结果
    assert result.name == "test"
```

---

## 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/agent/

# 运行带覆盖率的测试
pytest --cov=app
```

---

## 相关文档

- [编码规范](./coding-standards.md)
- [API 开发规范](./api-guidelines.md)
