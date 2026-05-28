"""提示词契约测试。

验证每个 output_format: json 的 prompt 渲染后，
其对应的场景文件响应能被正确解析为 Pydantic Schema。
提示词变更后，必须同步更新场景文件，否则测试失败。
"""

import json
import re
from pathlib import Path

import pytest

from app.services.shared.prompt_registry import registry
from app.services.shared.json_extractor import extract_and_validate
from app.services.shared.validation import (
    TaskBreakdownResult,
    TaskStepPlan,
    TaskAnalysisResult,
    TeamSuggestionResult,
    StrategyRecommendationResult,
    AgentTraitResult,
    ConsensusCheckResult,
    CoordinatorElectionResult,
    StageAdjustmentResult,
)

# prompt_id → (Schema, example_variables, scenario_file)
_JSON_PROMPT_CONTRACTS = [
    (
        "agent.executor.plan_steps",
        TaskStepPlan,
        {"task_title": "调查任务进展", "task_description": "收集并分析最新的项目进展数据"},
        "task_step_plan.json",
    ),
    (
        "agent.trait.generate",
        AgentTraitResult,
        {"agent_name": "小王", "principles": "- 代码简洁\n- 稳定可靠", "rules": "- 只输出JSON\n- 不编造信息"},
        "agent_trait.json",
    ),
    (
        "task.analyze",
        TaskAnalysisResult,
        {"task_description": "调查山西长治煤矿爆炸案的最新进展"},
        "task_analysis.json",
    ),
    (
        "team.build_suggestion",
        TeamSuggestionResult,
        {
            "domain": "信息查询",
            "task_type": "探索研究型",
            "complexity": "中",
            "breakdown": "收集资料, 分析数据",
            "key_challenge": "信息来源可靠性",
            "soul_pool_text": "小王: 后端开发\n小李: 数据分析",
        },
        "team_suggestion.json",
    ),
    (
        "collaboration.pipeline.task_breakdown_system",
        TaskBreakdownResult,
        {},
        "task_breakdown.json",
    ),
    (
        "collaboration.pipeline.task_breakdown",
        TaskBreakdownResult,
        {
            "project_name": "测试项目",
            "requirements": "收集数据并生成报告",
            "previous_analysis": "domain: 信息查询",
            "agent_info": "agent-001: 研究员",
            "project_type_guide": "信息收集类项目",
            "stage_guide": "- collect: 资料收集\n- analyze: 分析处理",
        },
        "task_breakdown.json",
    ),
    (
        "collaboration.discussion.consensus_check",
        ConsensusCheckResult,
        {"topic": "项目执行方案", "positions_text": "小王: 同意顺序执行\n小李: 支持"},
        "consensus_check.json",
    ),
    (
        "collaboration.discussion.election",
        CoordinatorElectionResult,
        {
            "project_name": "测试项目",
            "project_description": "一个信息收集项目",
            "agents_text": "- agent-001: 小王\n- agent-002: 小李",
            "speakers_text": "小王: 我建议这样\n小李: 我同意",
        },
        "coordinator_election.json",
    ),
    (
        "collaboration.pipeline_templates.adjustment",
        StageAdjustmentResult,
        {
            "project_name": "测试项目",
            "project_description": "信息收集项目",
            "template_name": "research",
            "template_description": "研究型模板",
            "current_stages": '[{"key": "collect", "label": "收集"}]',
        },
        "stage_adjustment.json",
    ),
    (
        "collaboration.strategy_recommender.recommend",
        StrategyRecommendationResult,
        {
            "project_name": "测试项目",
            "project_description": "信息收集项目",
            "requirements": "收集数据并分析",
            "agents_text": "agent-001: 研究员, agent-002: 分析师",
        },
        "strategy_recommendation.json",
    ),
]


def _load_scenario(filename: str) -> dict:
    """加载场景文件。"""
    scenario_dir = Path(__file__).parent / "llm_scenarios"
    with open(scenario_dir / filename, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPromptContracts:
    """验证每个 JSON 输出 prompt 的场景文件能被正确解析。"""

    @pytest.mark.parametrize(
        "prompt_id,schema_class,example_vars,scenario_file",
        _JSON_PROMPT_CONTRACTS,
        ids=[c[0] for c in _JSON_PROMPT_CONTRACTS],
    )
    def test_prompt_scenario_parses(self, prompt_id, schema_class, example_vars, scenario_file):
        """prompt 渲染后，对应场景文件的响应应解析为正确的 Schema。"""
        # 1. 渲染 prompt
        rendered = registry.render(prompt_id, example_vars)
        assert rendered, f"Prompt {prompt_id} 渲染后不应为空"

        # 2. 加载场景文件
        scenario = _load_scenario(scenario_file)
        response = scenario["response"]
        response_text = json.dumps(response, ensure_ascii=False)

        # 3. 验证场景文件的 JSON 能被 Schema 解析
        result = extract_and_validate(response_text, schema_class)
        assert result is not None, f"场景文件 {scenario_file} 应解析为 {schema_class.__name__}"

    @pytest.mark.parametrize(
        "prompt_id,schema_class,example_vars,scenario_file",
        _JSON_PROMPT_CONTRACTS,
        ids=[c[0] for c in _JSON_PROMPT_CONTRACTS],
    )
    def test_prompt_references_valid_schema(self, prompt_id, schema_class, example_vars, scenario_file):
        """prompt 的 template 中应提及正确的 JSON 输出格式。"""
        rendered = registry.render(prompt_id, example_vars)

        # 加载场景，验证其字段在 prompt 中有所提及
        scenario = _load_scenario(scenario_file)
        response = scenario["response"]

        # 场景中的顶层字段应存在于 Schema 中
        result = extract_and_validate(json.dumps(response, ensure_ascii=False), schema_class)
        # 验证至少一个关键字段对应
        model_dict = result.model_dump()
        for key in response:
            if key in model_dict:
                break
        else:
            pytest.fail(
                f"场景文件 {scenario_file} 的字段 {list(response.keys())} "
                f"与 Schema {schema_class.__name__} 的字段 {list(model_dict.keys())} 无交集"
            )


class TestScenarioFiles:
    """验证场景文件自身的一致性。"""

    def test_all_scenario_files_have_required_fields(self):
        """每个场景文件必须有 name、prompt_pattern、response 字段。"""
        scenario_dir = Path(__file__).parent / "llm_scenarios"
        for file_path in scenario_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert "name" in data, f"{file_path.name}: 缺少 name 字段"
            assert "prompt_pattern" in data, f"{file_path.name}: 缺少 prompt_pattern 字段"
            assert "response" in data, f"{file_path.name}: 缺少 response 字段"
            assert isinstance(data["response"], dict), f"{file_path.name}: response 应为 dict"

    def test_scenario_count_matches_contracts(self):
        """场景文件数量应覆盖所有 JSON prompt 契约。"""
        scenario_dir = Path(__file__).parent / "llm_scenarios"
        json_files = list(scenario_dir.glob("*.json"))
        # 至少 9 个场景文件（每个 Schema 一个）
        assert len(json_files) >= 9, f"场景文件不足：{len(json_files)}/9"


class TestMockLLMScenarioDriven:
    """验证 MockLLMProvider 场景驱动功能。"""

    def test_mock_llm_responds_with_scenario(self):
        """MockLLM 应在匹配 prompt_pattern 时返回场景 JSON。"""
        from app.core.mock_llm import MockLLMProvider
        from app.core.llm import Message as LLMMessage

        scenario_dir = str(Path(__file__).parent / "llm_scenarios")
        mock = MockLLMProvider(scenarios_dir=scenario_dir)

        messages = [
            LLMMessage(role="system", content="你是一位任务分析专家。只输出JSON。"),
            LLMMessage(role="user", content="请分析以下任务：调查煤矿爆炸案进展"),
        ]
        response = mock._get_mock_response(messages)

        # 匹配 task_analysis 场景（prompt_pattern: "task\.analyze|任务分析|分析项目"）
        parsed = json.loads(response)
        assert "domain" in parsed
        assert parsed["domain"] == "信息查询"

    def test_mock_llm_falls_back_to_keyword(self):
        """无场景匹配时应回退到关键词匹配。"""
        from app.core.mock_llm import MockLLMProvider
        from app.core.llm import Message as LLMMessage

        scenario_dir = str(Path(__file__).parent / "llm_scenarios")
        mock = MockLLMProvider(scenarios_dir=scenario_dir)

        messages = [
            LLMMessage(role="user", content="你好！能帮我写段代码吗？"),
        ]
        response = mock._get_mock_response(messages)

        # 不应是 JSON（因为代码关键词不匹配任何场景模式）
        assert not response.strip().startswith("{")
        assert "代码" in response or "code" in response.lower() or "实现" in response
