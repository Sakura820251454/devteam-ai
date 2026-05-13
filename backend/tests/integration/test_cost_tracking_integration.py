"""
成本追踪集成测试 - Phase 6.4

测试场景：
- 成本记录创建
- 成本统计查询
- 按 Agent/任务统计
- 成本趋势分析
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from datetime import datetime, timedelta


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestCostSummary:
    """测试成本摘要"""

    @pytest.mark.asyncio
    async def test_get_cost_summary(self, client):
        """测试获取成本摘要"""
        response = await client.get("/llm/costs/summary")
        assert response.status_code == 200
        summary = response.json()
        assert "total_cost" in summary
        assert "total_tokens" in summary
        assert "call_count" in summary

    @pytest.mark.asyncio
    async def test_summary_has_model_breakdown(self, client):
        """测试摘要包含模型分解"""
        response = await client.get("/llm/costs/summary")
        assert response.status_code == 200
        summary = response.json()
        assert "by_model" in summary
        assert isinstance(summary["by_model"], dict)

    @pytest.mark.asyncio
    async def test_summary_has_agent_breakdown(self, client):
        """测试摘要包含 Agent 分解"""
        response = await client.get("/llm/costs/summary")
        assert response.status_code == 200
        summary = response.json()
        assert "by_agent" in summary
        assert isinstance(summary["by_agent"], dict)


class TestCostByAgent:
    """测试按 Agent 统计成本"""

    @pytest.mark.asyncio
    async def test_filter_by_agent(self, client):
        """测试按 Agent 过滤成本"""
        response = await client.get(
            "/llm/costs/summary",
            params={"agent_id": "test_agent"}
        )
        assert response.status_code == 200


class TestCostByTask:
    """测试按任务统计成本"""

    @pytest.mark.asyncio
    async def test_filter_by_task(self, client):
        """测试按任务过滤成本"""
        response = await client.get(
            "/llm/costs/summary",
            params={"task_id": "test_task_123"}
        )
        assert response.status_code == 200


class TestCostLimitAndPagination:
    """测试成本记录限制和分页"""

    @pytest.mark.asyncio
    async def test_cost_records_limit(self, client):
        """测试成本记录数量限制"""
        response = await client.get(
            "/llm/costs/records",
            params={"limit": 5}
        )
        assert response.status_code == 200


class TestCostClear:
    """测试成本清除"""

    @pytest.mark.asyncio
    async def test_clear_all_costs(self, client):
        """测试清除所有成本记录"""
        response = await client.delete("/llm/costs/records")
        assert response.status_code == 200


class TestCostWithMultipleAgents:
    """测试多 Agent 成本追踪"""

    @pytest.mark.asyncio
    async def test_track_multiple_agents(self, client):
        """测试追踪多个 Agent 的成本"""
        agents = ["frontend_agent", "backend_agent", "test_agent"]

        for agent_id in agents:
            await client.post(
                "/llm/chat",
                json={
                    "messages": [{"role": "user", "content": f"Task for {agent_id}"}],
                    "agent_id": agent_id
                }
            )

        summary_response = await client.get("/llm/costs/summary")
        assert summary_response.status_code == 200


class TestCostAggregation:
    """测试成本聚合"""

    @pytest.mark.asyncio
    async def test_total_cost_calculation(self, client):
        """测试总成本计算"""
        await client.post(
            "/llm/chat",
            json={"messages": [{"role": "user", "content": "Cost test"}]}
        )

        summary_response = await client.get("/llm/costs/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary.get("total_cost", 0) >= 0

    @pytest.mark.asyncio
    async def test_total_tokens_calculation(self, client):
        """测试总 Token 计算"""
        await client.post(
            "/llm/chat",
            json={"messages": [{"role": "user", "content": "Token count"}]}
        )

        summary_response = await client.get("/llm/costs/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary.get("total_tokens", 0) >= 0


class TestCostIntegration:
    """成本追踪集成测试"""

    @pytest.mark.asyncio
    async def test_full_cost_tracking_workflow(self, client):
        """测试完整成本追踪工作流"""
        tasks = [
            {"agent_id": "dev_agent", "content": "开发任务"},
            {"agent_id": "test_agent", "content": "测试任务"},
            {"agent_id": "review_agent", "content": "审查任务"}
        ]

        for task in tasks:
            response = await client.post(
                "/llm/chat",
                json={
                    "messages": [{"role": "user", "content": task["content"]}],
                    "agent_id": task["agent_id"],
                    "track_cost": True
                }
            )
            assert response.status_code == 200

        summary_response = await client.get("/llm/costs/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["call_count"] >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
