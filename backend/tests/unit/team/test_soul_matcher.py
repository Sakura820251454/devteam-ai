"""SoulMatcher 单元测试 — Agent 人格匹配。

覆盖精确匹配 / 模糊匹配 / 兜底 / 全部占用 / 团队组建。
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.team.soul_matcher import SoulMatcher, SoulMatch, TeamFormation
from app.services.team.team_suggester import SuggestedRole, TeamSuggestion


def _make_role(role_name, suggested_soul="", responsibilities="", matching_reason=""):
    return SuggestedRole(
        role_name=role_name,
        responsibilities=responsibilities,
        suggested_soul=suggested_soul,
        matching_reason=matching_reason,
        priority="recommended",
        required_capabilities=[],
    )


def _make_suggestion(roles):
    return TeamSuggestion(
        team_name="测试团队",
        roles=roles,
        overall_rationale="测试用",
    )


SAMPLE_SOUL_AGENTS = [
    {"id": "soul-1", "name": "xiaoming", "type": "developer"},
    {"id": "soul-2", "name": "xiaohong", "type": "analyst"},
    {"id": "soul-3", "name": "xiaozhang", "type": "reviewer"},
]


class TestMatchRolesToSouls:
    """match_roles_to_souls 匹配流程。"""

    def test_no_soul_agents_returns_empty(self):
        matcher = SoulMatcher()
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            mock_svc.get_soul_based_agents.return_value = []
            suggestion = _make_suggestion([_make_role("研究员")])
            matches = matcher.match_roles_to_souls(suggestion)
            assert matches == []

    def test_exact_match_by_name(self):
        matcher = SoulMatcher()
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            mock_svc.get_soul_based_agents.return_value = SAMPLE_SOUL_AGENTS
            suggestion = _make_suggestion([
                _make_role("开发者", suggested_soul="xiaoming"),
            ])
            matches = matcher.match_roles_to_souls(suggestion)
            assert len(matches) == 1
            assert matches[0].soul_name == "xiaoming"
            assert matches[0].confidence == 0.9

    def test_fuzzy_match_by_name_contains(self):
        matcher = SoulMatcher()
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            mock_svc.get_soul_based_agents.return_value = SAMPLE_SOUL_AGENTS
            suggestion = _make_suggestion([
                _make_role("开发者", suggested_soul="xiao"),
            ])
            matches = matcher.match_roles_to_souls(suggestion)
            assert len(matches) == 1
            assert matches[0].confidence == 0.7

    def test_fallback_to_first_available(self):
        matcher = SoulMatcher()
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            mock_svc.get_soul_based_agents.return_value = SAMPLE_SOUL_AGENTS
            suggestion = _make_suggestion([
                _make_role("未知角色", suggested_soul="nonexistent_person"),
            ])
            matches = matcher.match_roles_to_souls(suggestion)
            assert len(matches) == 1
            assert matches[0].confidence == 0.4
            assert matches[0].soul_id == "soul-1"  # 第一个可用的

    def test_multiple_roles_different_souls(self):
        """多个角色不重复使用同一个 soul。"""
        matcher = SoulMatcher()
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            mock_svc.get_soul_based_agents.return_value = SAMPLE_SOUL_AGENTS
            suggestion = _make_suggestion([
                _make_role("角色A", suggested_soul="xiaoming"),
                _make_role("角色B", suggested_soul="xiaohong"),
            ])
            matches = matcher.match_roles_to_souls(suggestion)
            assert len(matches) == 2
            # 两个不同 soul
            soul_ids = {m.soul_id for m in matches}
            assert len(soul_ids) == 2

    def test_more_roles_than_souls(self):
        """角色多于 soul 时，只匹配可用数量。"""
        matcher = SoulMatcher()
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            mock_svc.get_soul_based_agents.return_value = SAMPLE_SOUL_AGENTS
            suggestion = _make_suggestion([
                _make_role(f"角色{i}") for i in range(5)
            ])
            matches = matcher.match_roles_to_souls(suggestion)
            assert len(matches) == 3  # 只有 3 个 soul

    def test_no_suggested_soul_uses_fallback(self):
        """没有 suggested_soul 时直接兜底。"""
        matcher = SoulMatcher()
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            mock_svc.get_soul_based_agents.return_value = SAMPLE_SOUL_AGENTS
            suggestion = _make_suggestion([
                _make_role("通用角色", suggested_soul=""),
            ])
            matches = matcher.match_roles_to_souls(suggestion)
            assert len(matches) == 1
            assert matches[0].confidence == 0.4


class TestFindBestMatch:
    """_find_best_match 各级匹配策略。"""

    def test_exact_match_confidence(self):
        matcher = SoulMatcher()
        role = _make_role("Dev", suggested_soul="xiaoming")
        match = matcher._find_best_match(role, SAMPLE_SOUL_AGENTS, set())
        assert match is not None
        assert match.confidence == 0.9
        assert match.soul_name == "xiaoming"

    def test_fuzzy_match_confidence(self):
        matcher = SoulMatcher()
        role = _make_role("Dev", suggested_soul="ming")
        match = matcher._find_best_match(role, SAMPLE_SOUL_AGENTS, set())
        assert match is not None
        assert match.confidence == 0.7

    def test_fallback_confidence(self):
        matcher = SoulMatcher()
        role = _make_role("Dev", suggested_soul="unknown_xyz")
        match = matcher._find_best_match(role, SAMPLE_SOUL_AGENTS, set())
        assert match is not None
        assert match.confidence == 0.4

    def test_all_used_returns_none(self):
        matcher = SoulMatcher()
        role = _make_role("Dev")
        # 所有 3 个 soul 都被占用了
        match = matcher._find_best_match(role, SAMPLE_SOUL_AGENTS, {"soul-1", "soul-2", "soul-3"})
        assert match is None


class TestCreateTeamInstances:
    """create_team_instances 组建团队。"""

    def test_assigns_agents(self):
        matcher = SoulMatcher()
        matches = [
            SoulMatch("Dev", "soul-1", "xiaoming", "写代码", 0.9, "匹配"),
        ]
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            formation = matcher.create_team_instances("proj-1", matches, "collaborative")
            mock_svc.assign_agent_to_project.assert_called_once_with("soul-1", "proj-1")
            assert formation.project_id == "proj-1"

    def test_hierarchical_sets_coordinator(self):
        matcher = SoulMatcher()
        matches = [
            SoulMatch("Lead", "soul-1", "xiaoming", "领导", 0.9, "匹配"),
            SoulMatch("Worker", "soul-2", "xiaohong", "执行", 0.7, "匹配"),
        ]
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            formation = matcher.create_team_instances("proj-1", matches, "hierarchical")
            assert formation.coordinator_id == "soul-1"

    def test_collaborative_no_coordinator(self):
        matcher = SoulMatcher()
        matches = [
            SoulMatch("A", "soul-1", "xiaoming", "", 0.9, ""),
        ]
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            formation = matcher.create_team_instances("proj-1", matches, "collaborative")
            assert formation.coordinator_id is None

    def test_assign_failure_graceful(self):
        """Agent 分配失败不影响其他匹配。"""
        matcher = SoulMatcher()
        matches = [
            SoulMatch("A", "soul-1", "xiaoming", "", 0.9, ""),
            SoulMatch("B", "soul-2", "xiaohong", "", 0.7, ""),
        ]
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            mock_svc.assign_agent_to_project.side_effect = [
                Exception("分配失败"),
                None,  # 第二个成功
            ]
            formation = matcher.create_team_instances("proj-1", matches, "collaborative")
            assert formation is not None
            assert mock_svc.assign_agent_to_project.call_count == 2

    def test_empty_matches(self):
        matcher = SoulMatcher()
        with patch("app.services.agent.agent_service.agent_service") as mock_svc:
            formation = matcher.create_team_instances("proj-1", [], "collaborative")
            assert formation.matches == []
