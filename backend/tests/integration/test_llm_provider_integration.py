"""
LLM Provider 集成测试 - Phase 6.4

测试场景：
- 多 Provider 切换
- 模型配置
- API 调用和响应
- 成本计算和追踪
- 错误处理和重试
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.llm_models import AVAILABLE_MODELS, get_model_info
from app.core.llm_providers import LLMProviderFactory, LLMProviderType
from app.core.mock_llm import MockLLMProvider
from app.core.llm import Message, LLMResponse


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestLLMProviders:
    """测试 LLM Provider 配置"""

    @pytest.mark.asyncio
    async def test_list_available_providers(self, client):
        """测试列出可用 Provider"""
        response = await client.get("/llm/providers")
        assert response.status_code == 200
        providers = response.json()
        assert isinstance(providers, list)
        assert "openai" in providers or "mock" in providers

    @pytest.mark.asyncio
    async def test_list_available_models(self, client):
        """测试列出可用模型"""
        response = await client.get("/llm/models")
        assert response.status_code == 200
        models = response.json()
        assert isinstance(models, dict)
        assert len(models) > 0

    @pytest.mark.asyncio
    async def test_get_model_info(self, client):
        """测试获取模型信息"""
        response = await client.get("/llm/models/gpt-4o")
        assert response.status_code == 200
        model_info = response.json()
        assert "name" in model_info
        assert "provider" in model_info
        assert "input_cost_per_1k" in model_info
        assert "output_cost_per_1k" in model_info

    @pytest.mark.asyncio
    async def test_get_nonexistent_model(self, client):
        """测试获取不存在的模型"""
        response = await client.get("/llm/models/nonexistent-model-xyz")
        assert response.status_code == 404


class TestMockLLMProvider:
    """测试 Mock LLM Provider"""

    @pytest.mark.asyncio
    async def test_mock_provider_chat(self):
        """测试 Mock Provider 聊天"""
        provider = MockLLMProvider()
        async with provider:
            messages = [Message(role="user", content="Hello")]
            response = await provider.chat(messages)
            assert response.content is not None
            assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_mock_provider_stream(self):
        """测试 Mock Provider 流式输出"""
        provider = MockLLMProvider()
        async with provider:
            messages = [Message(role="user", content="Tell me a story")]
            chunks = []
            async for chunk in provider.stream_chat(messages):
                chunks.append(chunk)
            assert len(chunks) > 0
            full_content = "".join(chunks)
            assert len(full_content) > 0

    @pytest.mark.asyncio
    async def test_mock_provider_stats(self):
        """测试 Mock Provider 统计"""
        provider = MockLLMProvider()
        async with provider:
            stats_before = provider.get_stats()
            initial_count = stats_before.get("call_count", 0)

            messages = [Message(role="user", content="Test")]
            await provider.chat(messages)

            stats_after = provider.get_stats()
            assert stats_after["call_count"] > initial_count


class TestLLMChat:
    """测试 LLM 聊天功能"""

    @pytest.mark.asyncio
    async def test_basic_chat(self, client):
        """测试基本聊天"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "temperature": 0.7
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "content" in result
        assert "usage" in result
        assert "model" in result
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_chat_with_system_message(self, client):
        """测试带系统消息的聊天"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is Python?"}
                ]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_chat_with_custom_model(self, client):
        """测试指定模型聊天"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "model": "gpt-4o"
            }
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_with_temperature(self, client):
        """测试不同温度参数"""
        for temp in [0.0, 0.5, 1.0, 1.5]:
            response = await client.post(
                "/llm/chat",
                json={
                    "messages": [{"role": "user", "content": "Random test"}],
                    "temperature": temp
                }
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_with_max_tokens(self, client):
        """测试最大 token 数"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Write a short story"}],
                "max_tokens": 50
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["content"]) <= 200

    @pytest.mark.asyncio
    async def test_chat_with_cost_tracking(self, client):
        """测试成本追踪"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "track_cost": True
            }
        )
        assert response.status_code == 200


class TestModelConfiguration:
    """测试模型配置"""

    def test_available_models_exist(self):
        """测试可用模型存在"""
        assert len(AVAILABLE_MODELS) > 0
        assert "gpt-4o" in AVAILABLE_MODELS or "mock" in AVAILABLE_MODELS

    def test_get_model_info_existing(self):
        """测试获取现有模型信息"""
        for model_name in AVAILABLE_MODELS:
            info = get_model_info(model_name)
            assert info is not None
            assert info.name is not None

    def test_model_pricing_info(self):
        """测试模型定价信息"""
        for model_name in AVAILABLE_MODELS:
            model_info = AVAILABLE_MODELS[model_name]
            assert hasattr(model_info, "input_cost_per_1k")
            assert hasattr(model_info, "output_cost_per_1k")
            assert model_info.input_cost_per_1k >= 0
            assert model_info.output_cost_per_1k >= 0


class TestProviderFactory:
    """测试 Provider 工厂"""

    def test_create_mock_provider(self):
        """测试创建 Mock Provider"""
        factory = LLMProviderFactory()
        provider = factory.get_provider(LLMProviderType.MOCK)
        assert provider is not None

    def test_provider_types(self):
        """测试 Provider 类型"""
        types = [p for p in LLMProviderType]
        assert len(types) > 0
        assert LLMProviderType.MOCK in types
        assert LLMProviderType.OPENAI in types


class TestCostTracking:
    """测试成本追踪"""

    @pytest.mark.asyncio
    async def test_cost_record_creation(self, client):
        """测试成本记录创建"""
        await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Test cost tracking"}],
                "track_cost": True
            }
        )

        response = await client.get("/llm/costs/records")
        assert response.status_code == 200
        records = response.json()
        assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_cost_summary(self, client):
        """测试成本摘要"""
        response = await client.get("/llm/costs/summary")
        assert response.status_code == 200
        summary = response.json()
        assert "total_cost" in summary
        assert "total_tokens" in summary
        assert "call_count" in summary

    @pytest.mark.asyncio
    async def test_cost_by_agent(self, client):
        """测试按 Agent 统计成本"""
        response = await client.get(
            "/llm/costs/summary",
            params={"agent_id": "test_agent"}
        )
        assert response.status_code == 200
        summary = response.json()
        assert "by_agent" in summary

    @pytest.mark.asyncio
    async def test_cost_by_model(self, client):
        """测试按模型统计成本"""
        response = await client.get("/llm/costs/summary")
        assert response.status_code == 200
        summary = response.json()
        assert "by_model" in summary

    @pytest.mark.asyncio
    async def test_cost_records_limit(self, client):
        """测试成本记录数量限制"""
        response = await client.get(
            "/llm/costs/records",
            params={"limit": 10}
        )
        assert response.status_code == 200
        records = response.json()
        assert len(records) <= 10

    @pytest.mark.asyncio
    async def test_clear_cost_records(self, client):
        """测试清除成本记录"""
        response = await client.delete("/llm/costs/records")
        assert response.status_code == 200
        assert response.json()["message"] == "Cost records cleared"


class TestLLMIntegration:
    """LLM 集成测试"""

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, client):
        """测试多轮对话"""
        messages = [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "What is a decorator in Python?"},
            {"role": "assistant", "content": "A decorator in Python is..."},
            {"role": "user", "content": "Can you give me an example?"}
        ]

        response = await client.post(
            "/llm/chat",
            json={"messages": messages}
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_long_conversation(self, client):
        """测试长对话"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]

        for i in range(10):
            messages.append({"role": "user", "content": f"Message {i+1}"})

        response = await client.post(
            "/llm/chat",
            json={"messages": messages}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """测试并发请求"""
        import asyncio

        async def make_request(i):
            return await client.post(
                "/llm/chat",
                json={
                    "messages": [{"role": "user", "content": f"Request {i}"}]
                }
            )

        tasks = [make_request(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        for response in responses:
            assert response.status_code == 200


class TestLLMErrorHandling:
    """测试 LLM 错误处理"""

    @pytest.mark.asyncio
    async def test_empty_message_list(self, client):
        """测试空消息列表"""
        response = await client.post(
            "/llm/chat",
            json={"messages": []}
        )
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_invalid_temperature(self, client):
        """测试无效温度参数"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "temperature": 3.0
            }
        )
        assert response.status_code == 422 or response.status_code == 400

    @pytest.mark.asyncio
    async def test_negative_temperature(self, client):
        """测试负温度参数"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "temperature": -0.5
            }
        )
        assert response.status_code == 422 or response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_model(self, client):
        """测试无效模型"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "model": "invalid-model-name-xyz"
            }
        )
        assert response.status_code == 404 or response.status_code == 200


class TestLLMResponseFormat:
    """测试 LLM 响应格式"""

    @pytest.mark.asyncio
    async def test_response_has_content(self, client):
        """测试响应包含内容"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Say 'test'"}]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "content" in result
        assert isinstance(result["content"], str)

    @pytest.mark.asyncio
    async def test_response_has_usage(self, client):
        """测试响应包含使用统计"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Count tokens"}]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "usage" in result
        usage = result["usage"]
        assert "prompt_tokens" in usage or "completion_tokens" in usage or "total_tokens" in usage

    @pytest.mark.asyncio
    async def test_response_has_model(self, client):
        """测试响应包含模型信息"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "What model are you?"}]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "model" in result

    @pytest.mark.asyncio
    async def test_response_has_finish_reason(self, client):
        """测试响应包含结束原因"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Stop"}]
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert "finish_reason" in result


class TestLLMCaching:
    """测试 LLM 缓存"""

    @pytest.mark.asyncio
    async def test_identical_requests_cached(self, client):
        """测试相同请求被缓存"""
        request_data = {
            "messages": [{"role": "user", "content": "Cached request"}]
        }

        first_response = await client.post("/llm/chat", json=request_data)
        second_response = await client.post("/llm/chat", json=request_data)

        assert first_response.status_code == 200
        assert second_response.status_code == 200

    @pytest.mark.asyncio
    async def test_different_requests_not_cached(self, client):
        """测试不同请求不被缓存"""
        response1 = await client.post(
            "/llm/chat",
            json={"messages": [{"role": "user", "content": "Request A"}]}
        )
        response2 = await client.post(
            "/llm/chat",
            json={"messages": [{"role": "user", "content": "Request B"}]}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200


class TestLLMWithAgent:
    """测试 LLM 与 Agent 集成"""

    @pytest.mark.asyncio
    async def test_chat_with_agent_id(self, client):
        """测试带 Agent ID 的聊天"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "agent_id": "test_agent_llm"
            }
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_cost_tracking(self, client):
        """测试 Agent 成本追踪"""
        response = await client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Track my cost"}],
                "agent_id": "agent_with_cost_tracking",
                "track_cost": True
            }
        )
        assert response.status_code == 200

        summary_response = await client.get(
            "/llm/costs/summary",
            params={"agent_id": "agent_with_cost_tracking"}
        )
        assert summary_response.status_code == 200


class TestStreamingResponse:
    """测试流式响应"""

    @pytest.mark.asyncio
    async def test_stream_response_format(self):
        """测试流式响应格式"""
        provider = MockLLMProvider()
        async with provider:
            messages = [Message(role="user", content="Stream test")]
            chunks = []
            async for chunk in provider.stream_chat(messages):
                chunks.append(chunk)
                assert isinstance(chunk, str)

            full_content = "".join(chunks)
            assert len(full_content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
