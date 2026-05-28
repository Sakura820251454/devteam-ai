"""解析器鲁棒性测试。

测试统一 JSON 提取器对各种 LLM 常见边界情况的处理能力。
无需真实 LLM — 纯逻辑测试。
"""

import pytest

from app.services.shared.json_extractor import (
    extract_json,
    extract_and_validate,
    JSONExtractionError,
    JSONValidationError,
)
from app.services.shared.validation import (
    TaskBreakdownResult,
    TaskStepPlan,
    TaskAnalysisResult,
    ConsensusCheckResult,
)


# ========== extract_json 基础测试 ==========


class TestJsonExtraction:
    """测试 JSON 提取核心逻辑。"""

    def test_pure_json(self):
        """纯 JSON 对象。"""
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        """JSON 前后有额外文本 — 常见于 LLM 输出。"""
        result = extract_json('这是一段分析文字。\n{"key": "value"}\n以上是结果。')
        assert result == {"key": "value"}

    def test_nested_braces(self):
        """嵌套大括号 — 平衡匹配的正确性验证。"""
        result = extract_json('{"outer": {"inner": "value"}, "list": [1, 2]}')
        assert result == {"outer": {"inner": "value"}, "list": [1, 2]}

    def test_nested_json_in_string(self):
        """JSON 字符串值中包含花括号字符。"""
        result = extract_json('{"code": "function foo() { return 1; }"}')
        assert result == {"code": "function foo() { return 1; }"}

    def test_trailing_comma(self):
        """尾随逗号 — LLM 最常见的 JSON 格式错误。"""
        result = extract_json('{"tasks": [{"title": "test", "phase": "x",}],}')
        assert "tasks" in result
        assert len(result["tasks"]) == 1

    def test_chinese_punctuation(self):
        """中文标点混用 — 全角逗号、冒号。"""
        result = extract_json('{"title"："中文标题"，"count"：3}')
        assert result.get("title") == "中文标题"
        assert result.get("count") == 3

    def test_single_quotes(self):
        """单引号替代双引号。"""
        result = extract_json("{'key': 'value'}")
        assert result == {"key": "value"}

    def test_markdown_code_block(self):
        """Markdown 代码块包裹的 JSON。"""
        text = '```json\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_inline_comments(self):
        """JSON 中的 // 注释行。"""
        result = extract_json('{\n// 这是一个注释\n"key": "value"\n}')
        assert result == {"key": "value"}

    def test_hash_comments(self):
        """JSON 中的 # 注释。"""
        result = extract_json('{\n# 注释\n"key": "value"\n}')
        assert result == {"key": "value"}

    def test_nan_infinity(self):
        """NaN / Infinity — Python 3.12 json 原生支持，解析为 float nan/inf。"""
        import math
        result = extract_json('{"a": NaN, "b": Infinity, "c": -Infinity}')
        assert math.isnan(result["a"])
        assert result["b"] == float("inf")
        assert result["c"] == float("-inf")

    def test_empty_text(self):
        """空字符串 — 应抛出异常。"""
        with pytest.raises(JSONExtractionError):
            extract_json("")

    def test_whitespace_only(self):
        """纯空白 — 应抛出异常。"""
        with pytest.raises(JSONExtractionError):
            extract_json("   \n\t  ")

    def test_no_json_present(self):
        """没有任何 JSON 的纯文本。"""
        with pytest.raises(JSONExtractionError):
            extract_json("这是纯文本，没有任何JSON结构。")

    def test_multiple_json_objects(self):
        """多个 JSON 对象 — 只提取第一个。"""
        result = extract_json('{"first": 1}\n{"second": 2}')
        assert result == {"first": 1}

    def test_array_extraction(self):
        """JSON 数组（方括号包裹）也应被正确提取。"""
        result = extract_json('["a", "b", "c"]')
        assert result == ["a", "b", "c"]


# ========== extract_and_validate 校验测试 ==========


class TestJsonValidation:
    """测试 Pydantic Schema 校验。"""

    def test_valid_task_breakdown(self):
        """合法的任务拆解 JSON。"""
        text = '{"tasks": [{"title": "T1", "phase": "collect"}], "summary": "ok"}'
        result = extract_and_validate(text, TaskBreakdownResult)
        assert len(result.tasks) == 1
        assert result.tasks[0].title == "T1"

    def test_task_breakdown_missing_fields(self):
        """缺少非必填字段 — 应使用默认值。"""
        text = '{"tasks": [{"title": "T1"}]}'
        result = extract_and_validate(text, TaskBreakdownResult)
        assert result.tasks[0].phase == "execution"  # 默认值
        assert result.tasks[0].priority == "medium"

    def test_task_breakdown_empty_tasks(self):
        """空任务列表 — 合法但无任务。"""
        text = '{"tasks": []}'
        result = extract_and_validate(text, TaskBreakdownResult)
        assert len(result.tasks) == 0

    def test_validation_error_on_wrong_type(self):
        """字段类型错误 — 应抛出 JSONValidationError。"""
        text = '{"tasks": [{"title": 123}]}'  # title 应为 str
        with pytest.raises(JSONValidationError):
            extract_and_validate(text, TaskBreakdownResult)

    def test_task_step_plan(self):
        """合法的步骤规划 JSON。"""
        text = '{"steps": [{"name": "步骤1", "description": "说明"}]}'
        result = extract_and_validate(text, TaskStepPlan)
        assert len(result.steps) == 1

    def test_consensus_check(self):
        """合法的共识检查 JSON。"""
        text = '{"consensus": true, "conclusion": "达成一致"}'
        result = extract_and_validate(text, ConsensusCheckResult)
        assert result.consensus is True

    def test_consensus_false(self):
        """未达成共识的检查。"""
        text = '{"consensus": false}'
        result = extract_and_validate(text, ConsensusCheckResult)
        assert result.consensus is False
        assert result.conclusion is None

    def test_task_analysis(self):
        """合法的项目分析 JSON。"""
        text = '{"domain": "信息查询", "task_type": "探索研究型", "complexity": "中"}'
        result = extract_and_validate(text, TaskAnalysisResult)
        assert result.domain == "信息查询"

    def test_unknown_extra_fields(self):
        """额外的未知字段 — Pydantic 默认忽略，不报错。"""
        text = '{"tasks": [{"title": "T1", "unknown_field": "xxx"}]}'
        result = extract_and_validate(text, TaskBreakdownResult)
        assert result.tasks[0].title == "T1"
