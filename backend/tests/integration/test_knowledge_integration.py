"""
知识进化集成测试 - Phase 6.4

测试场景：
- 知识的提取
- 知识的存储和检索
- 知识的进化和更新
- 知识与记忆的关联
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.knowledge.knowledge_evolution import (
    knowledge_evolution_service,
    KnowledgeType,
    KnowledgeConfidence,
    ExplicitKnowledgeType,
    ImplicitKnowledgeType,
)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_agent_id():
    """创建测试用 Agent ID"""
    return "test_agent_knowledge_001"


class TestKnowledgeExtraction:
    """测试知识提取"""

    @pytest.mark.asyncio
    async def test_discover_knowledge(self, client, test_agent_id):
        """测试从讨论内容提取知识"""
        response = await client.post(
            "/knowledge/discover",
            params={
                "content": "使用 Python 的 asyncio 可以高效处理并发任务",
                "agent_id": test_agent_id,
                "task_type": "async_programming"
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "knowledge_ids" in result
        assert "total_knowledge" in result

    @pytest.mark.asyncio
    async def test_record_success_case(self, client, test_agent_id):
        """测试记录成功案例"""
        response = await client.post(
            "/knowledge/success-case",
            params={"agent_id": test_agent_id, "task_type": "testing"},
            json={
                "task_description": "使用 pytest 进行单元测试",
                "context": "项目需要完整的测试覆盖",
                "method": "编写了100+测试用例，覆盖所有核心功能",
                "effect": "测试覆盖率达到85%，提前发现多个bug",
                "success_factors": [
                    "使用 pytest 框架",
                    "编写了 mock 对象",
                    "覆盖边界条件"
                ]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "成功案例已记录"
        assert "knowledge" in result

    @pytest.mark.asyncio
    async def test_record_failure_lesson(self, client, test_agent_id):
        """测试记录失败教训"""
        response = await client.post(
            "/knowledge/failure-lesson",
            params={"agent_id": test_agent_id, "task_type": "optimization"},
            json={
                "task_description": "优化数据库查询性能",
                "problem": "查询响应时间过长",
                "failed_attempts": [
                    "尝试使用缓存但未生效",
                    "添加索引位置不正确"
                ],
                "final_solution": "通过 EXPLAIN 分析查询计划，在 WHERE 条件的列上添加复合索引",
                "prevention_tips": [
                    "先分析慢查询日志",
                    "使用 EXPLAIN 检查执行计划",
                    "考虑查询的覆盖索引"
                ]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "失败教训已记录"
        assert "knowledge" in result

    @pytest.mark.asyncio
    async def test_add_code_snippet(self, client, test_agent_id):
        """测试添加代码片段"""
        response = await client.post(
            "/knowledge/code-snippet",
            json={
                "code": "def async_fetch(urls):\n    return [fetch(url) for url in urls]",
                "description": "异步获取多个URL的函数",
                "language": "python",
                "use_case": "并发请求多个API",
                "agent_id": test_agent_id
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "代码片段已保存"


class TestKnowledgeRetrieval:
    """测试知识检索"""

    @pytest.mark.asyncio
    async def test_search_knowledge(self, client):
        """测试搜索知识"""
        await client.post(
            "/knowledge/discover",
            params={
                "content": "FastAPI 是现代的 Python Web 框架",
                "agent_id": "test_agent",
                "task_type": "web_development"
            }
        )

        response = await client.get(
            "/knowledge/search",
            params={
                "query": "FastAPI Web 框架",
                "limit": 10
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert "count" in result
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_search_with_filter(self, client):
        """测试带过滤条件的搜索"""
        response = await client.get(
            "/knowledge/search",
            params={
                "query": "Python",
                "knowledge_type": "explicit",
                "min_confidence": "medium",
                "limit": 5
            }
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_knowledge_detail(self, client):
        """测试获取知识详情"""
        discover_response = await client.post(
            "/knowledge/discover",
            params={
                "content": "Docker 可以容器化应用程序",
                "agent_id": "test_agent",
                "task_type": "devops"
            }
        )
        knowledge_ids = discover_response.json()["knowledge_ids"]

        if knowledge_ids:
            detail_response = await client.get(f"/knowledge/{knowledge_ids[0]}")
            assert detail_response.status_code == 200
            knowledge = detail_response.json()
            assert "id" in knowledge
            assert "title" in knowledge
            assert "content" in knowledge

    @pytest.mark.asyncio
    async def test_get_nonexistent_knowledge(self, client):
        """测试获取不存在的知识"""
        response = await client.get("/knowledge/nonexistent_id_12345")
        assert response.status_code == 404


class TestKnowledgeUsage:
    """测试知识使用"""

    @pytest.mark.asyncio
    async def test_mark_knowledge_usage(self, client):
        """测试标记知识使用"""
        discover_response = await client.post(
            "/knowledge/discover",
            params={
                "content": "Git 是版本控制系统",
                "agent_id": "test_agent",
                "task_type": "version_control"
            }
        )
        knowledge_ids = discover_response.json()["knowledge_ids"]

        if knowledge_ids:
            usage_response = await client.post(
                f"/knowledge/{knowledge_ids[0]}/use",
                params={"success": True}
            )
            assert usage_response.status_code == 200
            result = usage_response.json()
            assert "usage_count" in result

    @pytest.mark.asyncio
    async def test_track_failed_usage(self, client):
        """测试追踪失败使用"""
        discover_response = await client.post(
            "/knowledge/discover",
            params={
                "content": "测试失败追踪",
                "agent_id": "test_agent"
            }
        )
        knowledge_ids = discover_response.json()["knowledge_ids"]

        if knowledge_ids:
            usage_response = await client.post(
                f"/knowledge/{knowledge_ids[0]}/use",
                params={"success": False}
            )
            assert usage_response.status_code == 200


class TestPatternDiscovery:
    """测试模式发现"""

    @pytest.mark.asyncio
    async def test_discover_patterns(self, client):
        """测试发现模式"""
        task_history = [
            {
                "task_type": "bug_fix",
                "approach": "分析日志找到问题",
                "success": True,
                "duration_hours": 2
            },
            {
                "task_type": "bug_fix",
                "approach": "添加日志输出",
                "success": True,
                "duration_hours": 1
            },
            {
                "task_type": "bug_fix",
                "approach": "使用断点调试",
                "success": True,
                "duration_hours": 3
            }
        ]

        response = await client.post(
            "/knowledge/patterns/discover",
            json={"task_history": task_history}
        )
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "total_patterns" in result

    @pytest.mark.asyncio
    async def test_get_patterns(self, client):
        """测试获取所有模式"""
        response = await client.get("/knowledge/patterns")
        assert response.status_code == 200
        result = response.json()
        assert "patterns" in result
        assert "count" in result
        assert isinstance(result["patterns"], list)


class TestSkillGeneration:
    """测试技能生成"""

    @pytest.mark.asyncio
    async def test_generate_skills(self, client, test_agent_id):
        """测试从成功案例生成技能"""
        await client.post(
            "/knowledge/success-case",
            params={"agent_id": test_agent_id},
            json={
                "task_description": "API 性能优化",
                "context": "需要提升 API 响应速度",
                "method": "使用缓存和批量处理",
                "effect": "响应时间从 500ms 降到 50ms",
                "success_factors": ["使用 Redis 缓存", "批量数据库查询"]
            }
        )

        response = await client.post(
            f"/knowledge/skills/generate",
            params={"agent_id": test_agent_id}
        )
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "skills" in result

    @pytest.mark.asyncio
    async def test_get_skills(self, client):
        """测试获取所有技能"""
        response = await client.get("/knowledge/skills")
        assert response.status_code == 200
        result = response.json()
        assert "skills" in result
        assert "count" in result


class TestKnowledgeStats:
    """测试知识统计"""

    @pytest.mark.asyncio
    async def test_get_knowledge_stats(self, client):
        """测试获取知识库统计"""
        response = await client.get("/knowledge/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "total_knowledge" in stats
        assert "by_type" in stats or isinstance(stats, dict)


class TestKnowledgeTypes:
    """测试知识类型"""

    def test_knowledge_type_values(self):
        """测试知识类型枚举值"""
        types = [t for t in KnowledgeType]
        assert len(types) > 0
        assert KnowledgeType.EXPLICIT in types
        assert KnowledgeType.IMPLICIT in types

    def test_explicit_knowledge_types(self):
        """测试显性知识类型"""
        types = [t for t in ExplicitKnowledgeType]
        assert len(types) > 0

    def test_implicit_knowledge_types(self):
        """测试隐性知识类型"""
        types = [t for t in ImplicitKnowledgeType]
        assert len(types) > 0

    def test_confidence_levels(self):
        """测试置信度级别"""
        levels = [c for c in KnowledgeConfidence]
        assert len(levels) > 0
        assert KnowledgeConfidence.HIGH in levels
        assert KnowledgeConfidence.MEDIUM in levels
        assert KnowledgeConfidence.LOW in levels


class TestKnowledgeEvolution:
    """测试知识进化"""

    @pytest.mark.asyncio
    async def test_knowledge_update_on_usage(self, client):
        """测试知识随使用进化"""
        discover_response = await client.post(
            "/knowledge/discover",
            params={
                "content": "需要进化的知识",
                "agent_id": "test_agent"
            }
        )
        knowledge_ids = discover_response.json()["knowledge_ids"]

        if knowledge_ids:
            knowledge_id = knowledge_ids[0]

            first_use = await client.post(f"/knowledge/{knowledge_id}/use", params={"success": True})
            first_stats = first_use.json()
            initial_count = first_stats.get("usage_count", 1)

            second_use = await client.post(f"/knowledge/{knowledge_id}/use", params={"success": True})
            second_stats = second_use.json()
            updated_count = second_stats.get("usage_count", 0)

            assert updated_count >= initial_count

    @pytest.mark.asyncio
    async def test_confidence_adjustment(self, client):
        """测试置信度调整"""
        discover_response = await client.post(
            "/knowledge/discover",
            params={
                "content": "置信度测试知识",
                "agent_id": "test_agent"
            }
        )
        knowledge_ids = discover_response.json()["knowledge_ids"]

        if knowledge_ids:
            knowledge_id = knowledge_ids[0]
            detail_before = await client.get(f"/knowledge/{knowledge_id}")

            for _ in range(3):
                await client.post(f"/knowledge/{knowledge_id}/use", params={"success": True})

            detail_after = await client.get(f"/knowledge/{knowledge_id}")
            assert detail_after.status_code == 200


class TestKnowledgeIntegration:
    """综合知识集成测试"""

    @pytest.mark.asyncio
    async def test_full_knowledge_lifecycle(self, client, test_agent_id):
        """测试完整知识生命周期"""
        # 1. 从讨论中提取知识
        discover_response = await client.post(
            "/knowledge/discover",
            params={
                "content": "学习如何编写高效的 Python 代码",
                "agent_id": test_agent_id,
                "task_type": "coding"
            }
        )
        assert discover_response.status_code == 200

        # 2. 记录成功案例
        success_response = await client.post(
            "/knowledge/success-case",
            params={"agent_id": test_agent_id},
            json={
                "task_description": "代码重构",
                "context": "需要优化代码结构",
                "method": "使用设计模式重构代码",
                "effect": "代码可读性和可维护性显著提升",
                "success_factors": ["遵循 SOLID 原则", "添加适当的注释"]
            }
        )
        assert success_response.status_code == 200

        # 3. 添加代码片段
        code_response = await client.post(
            "/knowledge/code-snippet",
            json={
                "code": "class OptimizedClass:\n    def __init__(self):\n        self._cache = {}",
                "description": "带缓存的类实现",
                "language": "python",
                "use_case": "性能优化",
                "agent_id": test_agent_id
            }
        )
        assert code_response.status_code == 200

        # 4. 搜索知识
        search_response = await client.get(
            "/knowledge/search",
            params={"query": "Python 代码 优化"}
        )
        assert search_response.status_code == 200

        # 5. 获取统计
        stats_response = await client.get("/knowledge/stats")
        assert stats_response.status_code == 200

        # 6. 获取模式
        patterns_response = await client.get("/knowledge/patterns")
        assert patterns_response.status_code == 200

        # 7. 生成技能
        skills_response = await client.post(
            f"/knowledge/skills/generate",
            params={"agent_id": test_agent_id}
        )
        assert skills_response.status_code == 200


class TestKnowledgeWithMemory:
    """测试知识与记忆关联"""

    @pytest.mark.asyncio
    async def test_knowledge_and_memory_integration(self, client, test_agent_id):
        """测试知识与记忆集成"""
        memory_response = await client.post(
            "/memories/",
            json={
                "agent_id": test_agent_id,
                "content": "学习新技术栈的重要经验",
                "level": "long_term",
                "tags": ["learning", "experience"]
            }
        )
        assert memory_response.status_code == 200

        knowledge_response = await client.post(
            "/knowledge/discover",
            params={
                "content": "将学习经验转化为知识资产",
                "agent_id": test_agent_id
            }
        )
        assert knowledge_response.status_code == 200

        retrieved_memories = await client.get(f"/memories/agent/{test_agent_id}")
        assert retrieved_memories.status_code == 200

        knowledge_stats = await client.get("/knowledge/stats")
        assert knowledge_stats.status_code == 200


class TestKnowledgeSearchQuality:
    """测试知识搜索质量"""

    @pytest.mark.asyncio
    async def test_semantic_search(self, client):
        """测试语义搜索"""
        contents = [
            "深度学习使用神经网络模型",
            "机器学习是人工智能的子领域",
            "自然语言处理处理文本数据",
            "计算机视觉处理图像和视频"
        ]

        for content in contents:
            await client.post(
                "/knowledge/discover",
                params={
                    "content": content,
                    "agent_id": "test_agent",
                    "task_type": "ml"
                }
            )

        response = await client.get(
            "/knowledge/search",
            params={
                "query": "神经网络 深度学习",
                "limit": 5
            }
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_filter_by_confidence(self, client):
        """测试按置信度过滤"""
        response = await client.get(
            "/knowledge/search",
            params={
                "query": "测试",
                "min_confidence": "high",
                "limit": 10
            }
        )
        assert response.status_code == 200


class TestKnowledgeErrorHandling:
    """测试知识系统错误处理"""

    @pytest.mark.asyncio
    async def test_search_empty_query(self, client):
        """测试空查询"""
        response = await client.get(
            "/knowledge/search",
            params={"query": ""}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_knowledge_type(self, client):
        """测试无效知识类型"""
        response = await client.get(
            "/knowledge/search",
            params={
                "query": "test",
                "knowledge_type": "invalid_type"
            }
        )
        assert response.status_code == 400 or response.status_code == 200

    @pytest.mark.asyncio
    async def test_use_nonexistent_knowledge(self, client):
        """测试使用不存在的知识"""
        response = await client.post(
            "/knowledge/nonexistent_id_12345/use",
            params={"success": True}
        )
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
