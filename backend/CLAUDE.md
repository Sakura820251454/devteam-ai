# Backend Rules

## Prompt management

所有 LLM prompt 的唯一来源是 `app/prompts/registry.yaml`。代码中禁止写 f-string prompt，使用 `registry.render(id, vars)`。改 prompt 后运行 `python scripts/prompt_doc_gen.py`。

## AI 输出安全网

- **AI 输出不可信任。** 入口处用 `extract_and_validate(text, Schema)` 做格式校验（`app/services/shared/json_extractor.py` + `validation.py`）。
- **一处实现。** 全项目统一使用上述提取器，禁止手写 `re.search(r"\{[\s\S]*\}", text)`。
- **失败要响亮。** 解析失败时：重试（附格式纠正提示）→ 仍失败则记录 warning（含原始输出摘要）→ 回退。禁止深层静默回退默认值。
- **加 Schema 就加场景文件。** 每个 Pydantic Schema 在 `tests/scenarios/llm_scenarios/` 下对应一个 JSON 场景文件。

## 状态机

- **`pipeline.status` 是唯一真相来源。** 禁止独立布尔值、禁止直接赋值 `pipeline.status = X`。
- **统一入口：** `PipelineOrchestrator.transition(pipeline, new_status)`，非法转移抛出 `IllegalStateTransition`。
- 合法转移矩阵定义在 `_ALLOWED_TRANSITIONS` 中。

## Testing

详见 `backend/tests/CLAUDE.md`。提交前运行 `pytest tests/ -x --tb=short`（`LLM_MODE=mock`）。
