# Testing Rules

## 测试架构

按被测对象的依赖类型分类：

| 类型 | 特征 | 策略 | 示例 |
|------|------|------|------|
| **纯逻辑** | 无外部依赖 | 参数化 table-driven | parser、state machine、validator |
| **LLM 依赖** | 解析 LLM 返回 | Mock LLM + 场景文件 | analyzer、suggester、orchestrator |
| **DB 依赖** | 数据库读写 | SQLite 内存库集成测试 | persistence 层 |
| **外部依赖** | 文件系统/网络 | stub + E2E 抽查 | workspace_manager、tool_executor |

## 目录规范

```
tests/
  unit/{domain}/test_{module}.py          # 纯逻辑单测
  integration/test_{module}_integration.py # DB/外部依赖集成测试
  e2e/test_{scenario}.py                  # 端到端
  scenarios/llm_scenarios/{name}.json     # LLM 场景文件
  scenarios/golden_paths/{name}.json      # Golden path 轨迹
  conftest.py                             # 共享 fixtures
  factories.py                            # 测试对象工厂
```

## 场景文件格式

`tests/scenarios/llm_scenarios/{name}.json`：

```json
{
  "name": "场景名称",
  "prompt_pattern": "正则匹配 LLM 输入的 prompt",
  "response": { /* 符合 Pydantic Schema 的 JSON 响应 */ }
}
```

MockLLM 优先按 `prompt_pattern` 匹配场景文件，未命中回退到关键词匹配。

## 新增规则

- **新加 Pydantic Schema** → 在 `llm_scenarios/` 下创建对应场景文件 + 在 `test_prompt_contracts.py` 注册
- **新加解析器** → 3 个边界测试：合法输入 / 缺失字段 / 格式错误
- **新加 DB 持久化类** → SQLite 集成测试
- **新加工具** → ToolDef schema 验证 + 执行 stub 测试
- **改 prompt** → 更新场景文件 + `test_prompt_contracts.py` 通过

## 运行

```bash
pytest tests/ -v              # 全量（LLM_MODE=mock）
pytest tests/unit/{domain}/   # 单模块
pytest tests/ -x --tb=short   # 遇错即停
```
