"""
记忆系统集成测试 - Phase 6.4

测试场景：
- 记忆的创建、读取、更新、删除
- 向量存储和检索
- 记忆压缩和增强
- 记忆持久化
- 跨会话记忆共享
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db, async_session_maker, engine
from app.models.agent_context import MemoryLevel


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_agent_id():
    """创建测试用 Agent ID"""
    return "test_agent_memory_001"


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """确保数据库初始化"""
    from app.database import init_db
    await init_db()
    yield


class TestMemoryCRUD:
    """测试记忆 CRUD 操作"""

    @pytest.mark.asyncio
    async def test_add_memory(self, client, test_agent_id):
        """测试添加记忆"""
        response = await client.post("/api/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "这是一个测试记忆内容",
                "level": MemoryLevel.WORKING.value,
                "tags": ["test", "memory"]
            }
        )
        assert response.status_code == 200
        memory = response.json()
        assert memory["content"] == "这是一个测试记忆内容"
        assert memory["level"] == MemoryLevel.WORKING.value
        assert memory["id"] is not None

    @pytest.mark.asyncio
    async def test_get_memory(self, client, test_agent_id):
        """测试获取记忆"""
        add_response = await client.post("/api/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "需要获取的记忆",
                "level": MemoryLevel.SHORT_TERM.value,
                "tags": ["test"]
            }
        )
        memory_id = add_response.json()["id"]

        get_response = await client.get(f"/api/memories/{memory_id}")
        assert get_response.status_code == 200
        memory = get_response.json()
        assert memory["id"] == memory_id
        assert memory["content"] == "需要获取的记忆"

    @pytest.mark.asyncio
    async def test_update_memory(self, client, test_agent_id):
        """测试更新记忆"""
        add_response = await client.post("/api/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "原始记忆内容",
                "level": MemoryLevel.WORKING.value
            }
        )
        memory_id = add_response.json()["id"]

        update_response = await client.put(f"/api/memories/{memory_id}",
            json={
                "content": "更新后的记忆内容",
                "tags": ["updated"]
            }
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["content"] == "更新后的记忆内容"
        assert "updated" in updated["tags"]

    @pytest.mark.asyncio
    async def test_delete_memory(self, client, test_agent_id):
        """测试删除记忆"""
        add_response = await client.post("/api/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "将被删除的记忆",
                "level": MemoryLevel.WORKING.value
            }
        )
        memory_id = add_response.json()["id"]

        delete_response = await client.delete(f"/api/memories/{memory_id}")
        assert delete_response.status_code == 200

        get_response = await client.get(f"/api/memories/{memory_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_agent_memories(self, client, test_agent_id):
        """测试获取 Agent 的所有记忆"""
        for i in range(3):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"记忆 {i+1}",
                    "level": MemoryLevel.WORKING.value
                }
            )

        response = await client.get(f"/api/memories/agent/{test_agent_id}")
        assert response.status_code == 200
        memories = response.json()
        assert len(memories) >= 3

    @pytest.mark.asyncio
    async def test_get_memories_by_level(self, client, test_agent_id):
        """测试按层级获取记忆"""
        levels = [MemoryLevel.WORKING, MemoryLevel.SHORT_TERM, MemoryLevel.LONG_TERM]
        for level in levels:
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"{level.value} 层级记忆",
                    "level": level.value
                }
            )

        for level in levels:
            response = await client.get(f"/api/memories/agent/{test_agent_id}",
                params={"level": level.value}
            )
            assert response.status_code == 200
            memories = response.json()
            assert all(m["level"] == level.value for m in memories)


class TestMemoryRetrieval:
    """测试记忆检索"""

    @pytest.mark.asyncio
    async def test_retrieve_memory_semantic(self, client, test_agent_id):
        """测试语义检索记忆"""
        memories_content = [
            "Python 是一种高级编程语言",
            "JavaScript 用于前端开发",
            "机器学习是人工智能的分支",
            "深度学习使用神经网络",
            "FastAPI 是一个现代的 Python Web 框架"
        ]

        for content in memories_content:
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": content,
                    "level": MemoryLevel.LONG_TERM.value,
                    "tags": ["knowledge"]
                }
            )

        response = await client.post("/api/memories/retrieve",
            json={
                "agent_id": test_agent_id,
                "search_query": "Python 编程",
                "use_semantic": True,
                "max_results": 5
            }
        )
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_retrieve_memory_with_filter(self, client, test_agent_id):
        """测试带过滤条件的检索"""
        await client.post("/api/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "重要的代码片段",
                "level": MemoryLevel.LONG_TERM.value,
                "tags": ["code", "important"]
            }
        )

        response = await client.post("/api/memories/retrieve",
            json={
                "agent_id": test_agent_id,
                "search_query": "代码",
                "level": MemoryLevel.LONG_TERM.value,
                "use_semantic": False,
                "max_results": 10
            }
        )
        assert response.status_code == 200


class TestMemoryPromotion:
    """测试记忆晋升"""

    @pytest.mark.asyncio
    async def test_promote_memory(self, client, test_agent_id):
        """测试记忆晋升到更高层级"""
        add_response = await client.post("/api/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "需要晋升的记忆",
                "level": MemoryLevel.WORKING.value
            }
        )
        memory_id = add_response.json()["id"]

        promote_response = await client.post(f"/api/memories/promote/{memory_id}",
            params={"to_level": MemoryLevel.LONG_TERM.value}
        )
        assert promote_response.status_code == 200
        promoted = promote_response.json()
        assert promoted["level"] == MemoryLevel.LONG_TERM.value


class TestMemoryStatistics:
    """测试记忆统计"""

    @pytest.mark.asyncio
    async def test_get_statistics(self, client, test_agent_id):
        """测试获取记忆统计"""
        for level in MemoryLevel:
            for i in range(2):
                await client.post("/api/memories/",
                    json={
                        "agent_id": test_agent_id,
                        "content": f"{level.value} 记忆 {i+1}",
                        "level": level.value
                    }
                )

        response = await client.get(f"/api/memories/agent/{test_agent_id}/statistics")
        assert response.status_code == 200
        stats = response.json()
        assert "working" in stats
        assert "short_term" in stats
        assert "long_term" in stats
        assert "total" in stats


class TestMemoryContext:
    """测试记忆上下文"""

    @pytest.mark.asyncio
    async def test_get_context_prompt(self, client, test_agent_id):
        """测试获取上下文提示词"""
        for i in range(5):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"上下文记忆 {i+1}",
                    "level": MemoryLevel.WORKING.value
                }
            )

        response = await client.get(f"/api/memories/context/{test_agent_id}/prompt")
        assert response.status_code == 200
        data = response.json()
        assert "prompt" in data
        assert len(data["prompt"]) > 0

    @pytest.mark.asyncio
    async def test_create_context(self, client, test_agent_id):
        """测试创建/更新上下文"""
        response = await client.post("/api/memories/context",
            json={
                "agent_id": test_agent_id,
                "role": "developer",
                "system_prompt": "你是一个专业的 Python 开发者",
                "personality": {"style": "详细"}
            }
        )
        assert response.status_code == 200


class TestMemoryCompression:
    """测试记忆压缩"""

    @pytest.mark.asyncio
    async def test_compress_context(self, client, test_agent_id):
        """测试上下文压缩"""
        for i in range(20):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"长记忆内容 {i+1}，" + "x" * 100,
                    "level": MemoryLevel.WORKING.value
                }
            )

        response = await client.post(f"/api/memories/agent/{test_agent_id}/compress",
            params={"max_tokens": 1000, "strategy": "auto"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "compression_ratio" in result["result"]

    @pytest.mark.asyncio
    async def test_get_compressed_prompt(self, client, test_agent_id):
        """测试获取压缩后的提示词"""
        for i in range(10):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"压缩测试记忆 {i+1}",
                    "level": MemoryLevel.WORKING.value
                }
            )

        response = await client.get(f"/api/memories/agent/{test_agent_id}/compressed-prompt",
            params={"max_tokens": 500}
        )
        assert response.status_code == 200
        data = response.json()
        assert "prompt" in data


class TestMemoryForgetting:
    """测试记忆遗忘"""

    @pytest.mark.asyncio
    async def test_get_forget_plan(self, client, test_agent_id):
        """测试获取遗忘计划"""
        for i in range(30):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"将被遗忘的记忆 {i+1}",
                    "level": MemoryLevel.WORKING.value
                }
            )

        response = await client.post(f"/api/memories/agent/{test_agent_id}/forget-plan")
        assert response.status_code == 200
        plan = response.json()
        assert "forget_plan" in plan

    @pytest.mark.asyncio
    async def test_auto_forget_dry_run(self, client, test_agent_id):
        """测试自动遗忘（干运行）"""
        for i in range(20):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"遗忘测试记忆 {i+1}",
                    "level": MemoryLevel.WORKING.value
                }
            )

        response = await client.post(f"/api/memories/agent/{test_agent_id}/auto-forget",
            params={"dry_run": True}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["dry_run"] is True

    @pytest.mark.asyncio
    async def test_capacity_check(self, client, test_agent_id):
        """测试容量检查"""
        response = await client.post(f"/api/memories/agent/{test_agent_id}/capacity-check")
        assert response.status_code == 200
        result = response.json()
        assert "capacity" in result
        assert "recommendations" in result


class TestMemoryDeduplication:
    """测试记忆去重"""

    @pytest.mark.asyncio
    async def test_deduplicate_memories(self, client, test_agent_id):
        """测试记忆去重"""
        for i in range(3):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": "重复的记忆内容",
                    "level": MemoryLevel.WORKING.value,
                    "tags": ["duplicate"]
                }
            )

        response = await client.post(f"/api/memories/agent/{test_agent_id}/deduplicate")
        assert response.status_code == 200
        result = response.json()
        assert "merged_count" in result["result"]


class TestMemoryRefresh:
    """测试记忆分数刷新"""

    @pytest.mark.asyncio
    async def test_refresh_memory_scores(self, client, test_agent_id):
        """测试刷新记忆分数"""
        for i in range(5):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"需要刷新分数的记忆 {i+1}",
                    "level": MemoryLevel.WORKING.value
                }
            )

        response = await client.post(f"/api/memories/agent/{test_agent_id}/refresh-scores")
        assert response.status_code == 200
        result = response.json()
        assert "statistics" in result


class TestMemoryExport:
    """测试记忆导出"""

    @pytest.mark.asyncio
    async def test_export_memories(self, client, test_agent_id):
        """测试导出记忆"""
        for i in range(3):
            await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"导出测试 {i+1}",
                    "level": MemoryLevel.WORKING.value,
                    "tags": ["export"]
                }
            )

        response = await client.post("/api/memories/export",
            json={"agent_id": test_agent_id}
        )
        assert response.status_code == 200
        result = response.json()
        assert "memories" in result
        assert "count" in result
        assert result["count"] >= 3


class TestMemoryQuality:
    """测试记忆质量"""

    @pytest.mark.asyncio
    async def test_get_memory_quality(self, client, test_agent_id):
        """测试获取记忆质量评分"""
        add_response = await client.post("/api/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "评估记忆质量",
                "level": MemoryLevel.WORKING.value
            }
        )
        memory_id = add_response.json()["id"]

        response = await client.get(f"/api/memories/quality/{memory_id}")
        assert response.status_code == 200
        quality = response.json()
        assert "quality" in quality


class TestCrossSessionMemory:
    """测试跨会话记忆共享"""

    @pytest.mark.asyncio
    async def test_shared_memory_across_sessions(self, client, test_agent_id):
        """测试跨会话记忆共享"""
        session1 = await client.post(
            "/api/sessions",
            json={"title": "会话1"}
        )
        session1_id = session1.json()["id"]

        await client.post("/api/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "跨会话共享的重要信息",
                "level": MemoryLevel.LONG_TERM.value,
                "session_id": session1_id,
                "tags": ["shared"]
            }
        )

        session2 = await client.post(
            "/api/sessions",
            json={"title": "会话2"}
        )
        session2_id = session2.json()["id"]

        memories = await client.get(f"/api/memories/agent/{test_agent_id}")
        assert memories.status_code == 200
        shared_memories = memories.json()
        assert any("跨会话共享" in m["content"] for m in shared_memories)


class TestMemoryIntegration:
    """综合记忆集成测试"""

    @pytest.mark.asyncio
    async def test_full_memory_lifecycle(self, client, test_agent_id):
        """测试完整记忆生命周期"""
        # 1. 添加多个层级的新记忆
        memories_ids = []
        for i, level in enumerate([MemoryLevel.WORKING, MemoryLevel.SHORT_TERM, MemoryLevel.LONG_TERM]):
            response = await client.post("/api/memories/",
                json={
                    "agent_id": test_agent_id,
                    "content": f"生命周期测试记忆 {i+1}",
                    "level": level.value,
                    "tags": ["lifecycle", f"level_{i}"]
                }
            )
            assert response.status_code == 200
            memories_ids.append(response.json()["id"])

        # 2. 检索记忆
        retrieved = await client.post("/api/memories/retrieve",
            json={
                "agent_id": test_agent_id,
                "search_query": "生命周期测试",
                "max_results": 10
            }
        )
        assert retrieved.status_code == 200

        # 3. 更新部分记忆
        await client.put(f"/api/memories/{memories_ids[0]}",
            json={"content": "更新后的生命周期测试记忆 1"}
        )

        # 4. 晋升记忆
        await client.post(f"/api/memories/promote/{memories_ids[0]}",
            params={"to_level": MemoryLevel.LONG_TERM.value}
        )

        # 5. 检查统计
        stats_response = await client.get(f"/api/memories/agent/{test_agent_id}/statistics")
        assert stats_response.status_code == 200

        # 6. 获取上下文提示词
        prompt_response = await client.get(f"/api/memories/context/{test_agent_id}/prompt")
        assert prompt_response.status_code == 200

        # 7. 验证最终状态
        final_memory = await client.get(f"/api/memories/{memories_ids[0]}")
        assert final_memory.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
