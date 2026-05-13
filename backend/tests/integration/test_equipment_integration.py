"""
装备系统集成测试 - Phase 6.4

测试场景：
- 装备的创建和初始化
- 装备的挂载和卸载
- 装备的使用和管理
- 装备槽位配置
- 装备与 Agent 的绑定
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_agent_id():
    """创建测试用 Agent ID"""
    return "test_agent_equipment_001"


class TestToolRegistry:
    """测试工具注册表"""

    @pytest.mark.asyncio
    async def test_register_tool(self, client):
        """测试注册新工具"""
        tool_data = {
            "name": "测试工具",
            "type": "mcp",
            "version": "1.0",
            "description": "用于生成测试代码的工具",
            "capabilities": ["test_generation", "mock_creation"],
            "suitable_tasks": ["testing", "qa"],
            "tokens": 100,
            "memory_mb": 50,
            "seconds": 5
        }

        response = await client.post("/equipment/tools", json=tool_data)
        assert response.status_code == 200
        result = response.json()
        assert "tool" in result
        assert result["tool"]["name"] == "测试工具"

    @pytest.mark.asyncio
    async def test_get_tool(self, client):
        """测试获取工具详情"""
        tool_data = {
            "name": "获取测试工具",
            "type": "mcp",
            "description": "MCP工具"
        }

        response = await client.post("/equipment/tools", json=tool_data)
        if response.status_code == 200:
            tool_id = response.json()["tool"]["id"]
            get_response = await client.get(f"/equipment/tools/{tool_id}")
            assert get_response.status_code == 200
            tool = get_response.json()
            assert tool["name"] == "获取测试工具"

    @pytest.mark.asyncio
    async def test_list_tools(self, client):
        """测试列出所有工具"""
        response = await client.get("/equipment/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert "count" in data
        assert isinstance(data["tools"], list)

    @pytest.mark.asyncio
    async def test_list_tools_by_type(self, client):
        """测试按类型列出工具"""
        response = await client.get("/equipment/tools", params={"tool_type": "mcp"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_tools_by_capability(self, client):
        """测试按能力列出工具"""
        response = await client.get("/equipment/tools", params={"capability": "coding"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_tools_by_task(self, client):
        """测试按任务类型列出工具"""
        response = await client.get("/equipment/tools", params={"task_type": "testing"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unregister_tool(self, client):
        """测试注销工具"""
        tool_data = {
            "name": "待注销工具",
            "type": "mcp",
            "description": "将被删除的工具"
        }

        response = await client.post("/equipment/tools", json=tool_data)
        if response.status_code == 200:
            tool_id = response.json()["tool"]["id"]
            delete_response = await client.delete(f"/equipment/tools/{tool_id}")
            assert delete_response.status_code == 200

            get_response = await client.get(f"/equipment/tools/{tool_id}")
            assert get_response.status_code == 404


class TestToolUsageTracking:
    """测试工具使用追踪"""

    @pytest.mark.asyncio
    async def test_update_tool_usage(self, client):
        """测试更新工具使用统计"""
        tool_data = {
            "name": "使用统计工具",
            "type": "mcp",
            "description": "用于测试使用统计"
        }

        response = await client.post("/equipment/tools", json=tool_data)
        if response.status_code == 200:
            tool_id = response.json()["tool"]["id"]
            usage_response = await client.post(
                f"/equipment/tools/{tool_id}/usage",
                params={
                    "agent_id": "test_agent",
                    "success": True,
                    "execution_time": 2.5
                }
            )
            assert usage_response.status_code == 200
            result = usage_response.json()
            assert result["message"] == "Usage stats updated"

    @pytest.mark.asyncio
    async def test_tool_stats(self, client):
        """测试获取工具统计"""
        response = await client.get("/equipment/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "total_tools" in stats
        assert "by_type" in stats


class TestTaskAnalysis:
    """测试任务分析"""

    @pytest.mark.asyncio
    async def test_analyze_task(self, client, test_agent_id):
        """测试分析任务需求"""
        response = await client.post(
            f"/equipment/agent/{test_agent_id}/analyze",
            params={"task_description": "开发一个Python Web应用"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "required_tools" in result
        assert "optional_tools" in result
        assert "confidence" in result


class TestEquipmentManagement:
    """测试装备管理"""

    @pytest.mark.asyncio
    async def test_equip_tools(self, client, test_agent_id):
        """测试装备工具"""
        response = await client.post(
            f"/equipment/agent/{test_agent_id}/equip",
            params={"task_description": "编写单元测试"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "equipped_tools" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_get_agent_equipment(self, client, test_agent_id):
        """测试获取 Agent 装备状态"""
        response = await client.get(f"/equipment/agent/{test_agent_id}/equipment")
        assert response.status_code == 200
        equipment = response.json()
        assert "equipped_tools" in equipment
        assert "capabilities" in equipment

    @pytest.mark.asyncio
    async def test_unequip_tool(self, client, test_agent_id):
        """测试卸载指定工具"""
        await client.post(
            f"/equipment/agent/{test_agent_id}/equip",
            params={"task_description": "测试任务"}
        )

        equipment_response = await client.get(f"/equipment/agent/{test_agent_id}/equipment")
        equipped_tools = equipment_response.json().get("equipped_tools", [])

        if equipped_tools:
            tool_id = equipped_tools[0]["id"]
            unequip_response = await client.post(
                f"/equipment/agent/{test_agent_id}/unequip/{tool_id}"
            )
            assert unequip_response.status_code == 200

    @pytest.mark.asyncio
    async def test_unequip_all_tools(self, client, test_agent_id):
        """测试卸载所有工具"""
        await client.post(
            f"/equipment/agent/{test_agent_id}/equip",
            params={"task_description": "先装备工具"}
        )

        unequip_all_response = await client.post(
            f"/equipment/agent/{test_agent_id}/unequip-all"
        )
        assert unequip_all_response.status_code == 200


class TestEquipmentServiceIntegration:
    """测试装备服务集成"""

    @pytest.mark.asyncio
    async def test_full_equipment_cycle(self, client, test_agent_id):
        """测试完整装备周期"""
        tool_data = {
            "name": "集成测试工具",
            "type": "mcp",
            "version": "1.0",
            "description": "用于集成测试的工具",
            "capabilities": ["data_analysis", "transformation"],
            "suitable_tasks": ["etl", "analytics"],
            "tokens": 200,
            "memory_mb": 100,
            "seconds": 10
        }
        create_response = await client.post("/equipment/tools", json=tool_data)
        assert create_response.status_code == 200
        tool_id = create_response.json()["tool"]["id"]

        get_response = await client.get(f"/equipment/tools/{tool_id}")
        assert get_response.status_code == 200

        analyze_response = await client.post(
            f"/equipment/agent/{test_agent_id}/analyze",
            params={"task_description": "数据分析和转换"}
        )
        assert analyze_response.status_code == 200

        equip_response = await client.post(
            f"/equipment/agent/{test_agent_id}/equip",
            params={"task_description": "数据分析任务"}
        )
        assert equip_response.status_code == 200

        status_response = await client.get(f"/equipment/agent/{test_agent_id}/equipment")
        assert status_response.status_code == 200

        stats_response = await client.get("/equipment/stats")
        assert stats_response.status_code == 200


class TestEquipmentWithAgent:
    """测试装备与 Agent 绑定"""

    @pytest.mark.asyncio
    async def test_equip_to_multiple_agents(self, client):
        """测试向多个 Agent 装备"""
        agent1_id = "test_agent_equipment_multi_1"
        agent2_id = "test_agent_equipment_multi_2"

        await client.post(
            f"/equipment/agent/{agent1_id}/equip",
            params={"task_description": "Agent1的任务"}
        )

        await client.post(
            f"/equipment/agent/{agent2_id}/equip",
            params={"task_description": "Agent2的任务"}
        )

        equipment1 = await client.get(f"/equipment/agent/{agent1_id}/equipment")
        equipment2 = await client.get(f"/equipment/agent/{agent2_id}/equipment")

        assert equipment1.status_code == 200
        assert equipment2.status_code == 200


class TestToolCapabilities:
    """测试工具能力"""

    @pytest.mark.asyncio
    async def test_tool_capabilities_tracking(self, client):
        """测试工具能力追踪"""
        tool_data = {
            "name": "能力测试工具",
            "type": "mcp",
            "capabilities": ["code_generation", "refactoring", "optimization"],
            "suitable_tasks": ["development", "refactoring"]
        }

        create_response = await client.post("/equipment/tools", json=tool_data)
        if create_response.status_code == 200:
            tool_id = create_response.json()["tool"]["id"]
            get_response = await client.get(f"/equipment/tools/{tool_id}")
            if get_response.status_code == 200:
                tool = get_response.json()
                assert "code_generation" in tool["capabilities"]


class TestResourceCost:
    """测试资源成本"""

    @pytest.mark.asyncio
    async def test_tool_with_resource_cost(self, client):
        """测试带资源成本注册工具"""
        tool_data = {
            "name": "成本测试工具",
            "type": "mcp",
            "description": "带资源成本的工具",
            "tokens": 1000,
            "memory_mb": 512,
            "seconds": 60
        }

        response = await client.post("/equipment/tools", json=tool_data)
        assert response.status_code == 200
        tool = response.json()["tool"]
        assert tool["resource_cost"]["tokens"] == 1000
        assert tool["resource_cost"]["memory_mb"] == 512
        assert tool["resource_cost"]["seconds"] == 60


class TestEquipmentErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_get_nonexistent_tool(self, client):
        """测试获取不存在的工具"""
        response = await client.get("/equipment/tools/nonexistent_tool_12345")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_tool_type(self, client):
        """测试无效的工具类型"""
        tool_data = {
            "name": "无效类型工具",
            "type": "invalid_tool_type_xyz",
            "description": "使用无效类型"
        }

        response = await client.post("/equipment/tools", json=tool_data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_unequip_nonexistent_tool(self, client, test_agent_id):
        """测试卸载不存在的工具"""
        response = await client.post(
            f"/equipment/agent/{test_agent_id}/unequip/nonexistent_tool"
        )
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
