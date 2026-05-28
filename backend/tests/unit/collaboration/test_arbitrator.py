"""冲突仲裁器单元测试。

测试冲突检测规则、投票逻辑、裁决决策。
纯逻辑测试，不依赖 LLM。
"""

import pytest

from app.services.collaboration.arbitrator import (
    ConflictArbitrator,
    ArbitrationIssue,
    ArbitrationStatus,
    VoteType,
)


# ========== ArbitrationIssue ==========


class TestArbitrationIssue:
    """仲裁议题数据类测试。"""

    def test_default_status_is_pending(self):
        issue = ArbitrationIssue(
            id="arb_001",
            task_id="task-1",
            title="测试冲突",
            description="两个 Agent 结论不同",
        )
        assert issue.status == ArbitrationStatus.PENDING
        assert issue.votes == {}
        assert issue.resolution is None

    def test_proposals_list(self):
        issue = ArbitrationIssue(
            id="arb_002",
            task_id="task-2",
            title="分歧",
            description="结论不一致",
            proposals=[
                {"agent_id": "a1", "agent_name": "小王", "position": "方案A", "reasoning": "更高效"},
                {"agent_id": "a2", "agent_name": "小李", "position": "方案B", "reasoning": "更安全"},
            ],
        )
        assert len(issue.proposals) == 2
        assert issue.proposals[0]["agent_name"] == "小王"


# ========== 共享 fixtures ==========


def _make_issue(task_id="task-1", status=ArbitrationStatus.PENDING):
    """快速创建测试用 ArbitrationIssue（同步）。"""
    return ArbitrationIssue(
        id=f"arb_test_{task_id}",
        task_id=task_id,
        title=f"冲突: {task_id}",
        description="测试冲突",
        proposals=[
            {"agent_id": "a1", "agent_name": "小王", "position": "方案A", "reasoning": "理由A"},
            {"agent_id": "a2", "agent_name": "小李", "position": "方案B", "reasoning": "理由B"},
        ],
        status=status,
    )


def _make_arb_with_issue(status=ArbitrationStatus.PENDING):
    """创建带有一个 issue 的 ConflictArbitrator（同步）。"""
    arb = ConflictArbitrator()
    issue = _make_issue(status=status)
    arb._issues[issue.id] = issue
    return arb, issue


# ========== ConflictArbitrator 冲突检测 ==========


class TestConflictDetection:
    """detect_conflict 冲突检测测试。"""

    @pytest.fixture
    def arbitrator(self):
        return ConflictArbitrator()

    @pytest.mark.asyncio
    async def test_no_conflict_single_agent(self, arbitrator):
        result = await arbitrator.detect_conflict("task-1", [
            {"agent_id": "a1", "conclusion": "一切正常"},
        ])
        assert result is None

    @pytest.mark.asyncio
    async def test_no_conflict_identical_conclusions(self, arbitrator):
        result = await arbitrator.detect_conflict("task-1", [
            {"agent_id": "a1", "conclusion": "通过"},
            {"agent_id": "a2", "conclusion": "通过"},
        ])
        assert result is None

    @pytest.mark.asyncio
    async def test_conflict_detected_different_conclusions(self, arbitrator):
        issue = await arbitrator.detect_conflict("task-1", [
            {"agent_id": "a1", "agent_name": "小王", "conclusion": "方案A可行", "reasoning": "理由A"},
            {"agent_id": "a2", "agent_name": "小李", "conclusion": "方案B更好", "reasoning": "理由B"},
        ])
        assert issue is not None
        assert issue.task_id == "task-1"
        assert len(issue.proposals) == 2
        assert issue.status == ArbitrationStatus.PENDING

    @pytest.mark.asyncio
    async def test_conflict_empty_conclusion_filtered(self, arbitrator):
        result = await arbitrator.detect_conflict("task-1", [
            {"agent_id": "a1", "conclusion": "方案A"},
            {"agent_id": "a2", "conclusion": ""},
            {"agent_id": "a3", "conclusion": ""},
        ])
        assert result is None


# ========== 投票逻辑 ==========


class TestVoting:
    """cast_vote 投票测试。"""

    @pytest.mark.asyncio
    async def test_cast_vote_success(self):
        arb, issue = _make_arb_with_issue(status=ArbitrationStatus.VOTING)
        result = await arb.cast_vote(issue.id, "a1", VoteType.AGREE)
        assert result["agent_id"] == "a1"
        assert result["vote"] == "agree"

    @pytest.mark.asyncio
    async def test_vote_on_non_voting_issue_fails(self):
        arb, issue = _make_arb_with_issue(status=ArbitrationStatus.PENDING)
        result = await arb.cast_vote(issue.id, "a1", VoteType.AGREE)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_vote_on_nonexistent_issue(self):
        arb = ConflictArbitrator()
        with pytest.raises(ValueError, match="not found"):
            await arb.cast_vote("no-such-issue", "a1", VoteType.AGREE)


# ========== 裁决逻辑 ==========


class TestResolution:
    """_resolve 裁决逻辑测试。"""

    @pytest.mark.asyncio
    async def test_majority_agree_resolves(self):
        arb, issue = _make_arb_with_issue(status=ArbitrationStatus.VOTING)
        issue.votes = {"a1": VoteType.AGREE, "a2": VoteType.AGREE}
        result = await arb._resolve(issue)
        assert result["status"] == "resolved"
        # 多数同意时应包含相应文本
        resolution_text = result.get("resolution", "")
        assert resolution_text

    @pytest.mark.asyncio
    async def test_majority_disagree_uses_meta_agent(self):
        arb, issue = _make_arb_with_issue(status=ArbitrationStatus.VOTING)
        issue.votes = {"a1": VoteType.DISAGREE, "a2": VoteType.DISAGREE}
        result = await arb._resolve(issue)
        assert result["resolved_by"] == "meta_agent"

    @pytest.mark.asyncio
    async def test_tie_votes_deadlocks(self):
        arb, issue = _make_arb_with_issue(status=ArbitrationStatus.VOTING)
        issue.votes = {"a1": VoteType.AGREE, "a2": VoteType.DISAGREE}
        result = await arb._resolve(issue)
        assert result["status"] == "deadlocked"
        assert "人工" in result.get("resolution", "")

    @pytest.mark.asyncio
    async def test_abstain_majority_wins(self):
        arb, issue = _make_arb_with_issue(status=ArbitrationStatus.VOTING)
        issue.votes = {"a1": VoteType.AGREE, "a2": VoteType.ABSTAIN}
        result = await arb._resolve(issue)
        assert result["status"] == "resolved"


# ========== 人工裁决和查询 ==========


class TestManualResolution:
    """人工裁决和议题管理。"""

    def test_get_issue(self):
        arb, issue = _make_arb_with_issue()
        retrieved = arb.get_issue(issue.id)
        assert retrieved is issue

    def test_get_issue_not_found(self):
        arb = ConflictArbitrator()
        assert arb.get_issue("no-such") is None

    def test_manually_resolve(self):
        arb, issue = _make_arb_with_issue()
        result = arb.manually_resolve(issue.id, "选择方案A", "admin")
        assert result is not None
        assert result["status"] == "resolved"
        assert result["resolution"] == "选择方案A"
        assert result["resolved_by"] == "admin"
        assert issue.status == ArbitrationStatus.RESOLVED

    def test_manually_resolve_not_found(self):
        arb = ConflictArbitrator()
        assert arb.manually_resolve("no-such", "x", "admin") is None

    @pytest.mark.asyncio
    async def test_escalate_to_human(self):
        arb, issue = _make_arb_with_issue()
        result = await arb.escalate_to_human(issue.id)
        assert result["status"] == "deadlocked"
        assert "人工" in result["message"]
        assert len(result["proposals"]) == 2

    def test_list_issues_filter_by_status(self):
        arb, issue = _make_arb_with_issue(status=ArbitrationStatus.DEADLOCKED)
        issues = arb.list_issues(status=ArbitrationStatus.DEADLOCKED)
        assert len(issues) == 1
        assert issues[0]["id"] == issue.id

    def test_list_issues_filter_by_task_id(self):
        arb, issue = _make_arb_with_issue()
        issues = arb.list_issues(task_id="task-1")
        assert len(issues) == 1

    def test_list_issues_filter_by_nonexistent(self):
        arb, issue = _make_arb_with_issue()
        issues = arb.list_issues(status=ArbitrationStatus.RESOLVED)
        assert len(issues) == 0

    def test_clear_project_issues(self):
        arb, issue = _make_arb_with_issue()
        issue.project_id = "proj-del"
        assert len(arb.list_issues()) == 1
        arb.clear_project_issues("proj-del")
        assert len(arb.list_issues()) == 0

    def test_clear_non_matching_project(self):
        arb, issue = _make_arb_with_issue()
        issue.project_id = "proj-keep"
        arb.clear_project_issues("proj-other")
        assert len(arb.list_issues()) == 1
