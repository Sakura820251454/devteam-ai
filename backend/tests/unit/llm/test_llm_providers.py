import pytest
import asyncio
from app.core.llm_models import (
    LLMProviderType,
    AVAILABLE_MODELS,
    get_model_info,
    calculate_cost,
    LLMModelInfo
)
from app.core.llm_providers import (
    LLMProviderFactory,
    BaseLLMProvider,
    DeepSeekProvider,
    OpenAIProvider
)
from app.core.mock_llm import MockLLMProvider
from app.core.llm import Message


class TestLLMModels:
    def test_provider_types(self):
        assert LLMProviderType.OPENAI.value == "openai"
        assert LLMProviderType.DEEPSEEK.value == "deepseek"
        assert LLMProviderType.ANTHROPIC.value == "anthropic"
        assert LLMProviderType.MOCK.value == "mock"

    def test_available_models(self):
        assert "gpt-4o" in AVAILABLE_MODELS
        assert "deepseek-v4-flash" in AVAILABLE_MODELS
        assert "mock-model" in AVAILABLE_MODELS
        
        model = AVAILABLE_MODELS["deepseek-v4-flash"]
        assert model.provider == LLMProviderType.DEEPSEEK
        assert model.input_cost_per_1k == 0.001
        assert model.output_cost_per_1k == 0.002

    def test_get_model_info(self):
        model_info = get_model_info("deepseek-v4-flash")
        assert model_info.name == "deepseek-v4-flash"
        assert model_info.provider == LLMProviderType.DEEPSEEK

    def test_get_model_info_default(self):
        model_info = get_model_info("unknown-model")
        assert model_info.name == "deepseek-v4-flash"  # falls back to default provider model

    def test_calculate_cost_deepseek(self):
        cost = calculate_cost("deepseek-v4-flash", 1000, 500)
        expected = (1000 / 1000) * 0.001 + (500 / 1000) * 0.002
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_openai(self):
        cost = calculate_cost("gpt-4o", 1000, 1000)
        expected = (1000 / 1000) * 5.0 + (1000 / 1000) * 15.0
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_mock(self):
        cost = calculate_cost("mock-model", 1000, 1000)
        assert cost == 0.0


class TestMockProvider:
    @pytest.fixture
    def provider(self):
        p = MockLLMProvider()
        yield p

    @pytest.mark.asyncio
    async def test_chat_basic(self, provider):
        messages = [Message(role="user", content="你好")]
        response = await provider.chat(messages)

        assert response.content is not None
        assert len(response.content) > 0
        assert response.model == "mock-model"
        assert "total_tokens" in response.usage

    @pytest.mark.asyncio
    async def test_chat_greeting(self, provider):
        messages = [Message(role="user", content="你好！")]
        response = await provider.chat(messages)

        assert "你好" in response.content or "开发者" in response.content

    @pytest.mark.asyncio
    async def test_chat_code(self, provider):
        messages = [Message(role="user", content="帮我写代码")]
        response = await provider.chat(messages)

        assert "代码" in response.content or "```" in response.content

    @pytest.mark.asyncio
    async def test_stream_chat(self, provider):
        messages = [Message(role="user", content="你好")]
        chunks = []

        async for chunk in provider.stream_chat(messages):
            chunks.append(chunk)

        full_content = "".join(chunks)
        assert len(full_content) > 0

    @pytest.mark.asyncio
    async def test_stats(self, provider):
        messages = [Message(role="user", content="你好")]
        await provider.chat(messages)
        await provider.chat(messages)

        stats = provider.get_stats()
        assert stats["call_count"] == 2
        assert stats["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_reset_stats(self, provider):
        messages = [Message(role="user", content="你好")]
        await provider.chat(messages)
        provider.reset_stats()

        stats = provider.get_stats()
        assert stats["call_count"] == 0


class TestLLMProviderFactory:
    def test_get_mock_provider(self):
        provider = LLMProviderFactory.get_provider(LLMProviderType.MOCK)
        assert isinstance(provider, MockLLMProvider)

    def test_get_available_providers(self):
        providers = LLMProviderFactory.get_available_providers()
        assert "openai" in providers
        assert "deepseek" in providers
        assert "anthropic" in providers
        assert "mock" in providers

    def test_get_models_by_provider(self):
        models = LLMProviderFactory.get_models_by_provider(LLMProviderType.DEEPSEEK)
        assert len(models) > 0
        assert all(m.provider == LLMProviderType.DEEPSEEK for m in models)

    def test_get_all_models(self):
        models = LLMProviderFactory.get_all_models()
        assert "deepseek-v4-flash" in models
        assert "gpt-4o" in models


class TestLLMConfig:
    def test_llm_config_defaults(self):
        from app.models.agent import LLMConfig, LLMProviderType

        config = LLMConfig()
        assert config.provider == LLMProviderType.DEEPSEEK
        assert config.model == "deepseek-v4-flash"
        assert config.temperature == 0.7

    def test_llm_config_custom(self):
        from app.models.agent import LLMConfig, LLMProviderType
        
        config = LLMConfig(
            provider=LLMProviderType.DEEPSEEK,
            model="deepseek-v4-flash",
            temperature=0.5,
            max_tokens=2000
        )
        assert config.provider == LLMProviderType.DEEPSEEK
        assert config.model == "deepseek-v4-flash"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000

    def test_agent_config_with_llm(self):
        from app.models.agent import Agent, AgentConfig, LLMConfig, LLMProviderType
        
        config = AgentConfig(
            name="Test Agent",
            role="Developer",
            llm_config=LLMConfig(
                provider=LLMProviderType.DEEPSEEK,
                model="deepseek-v4-flash"
            )
        )
        assert config.llm_config is not None
        assert config.llm_config.provider == LLMProviderType.DEEPSEEK


class TestMessage:
    def test_message_creation(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_to_dict(self):
        msg = Message(role="user", content="Hello")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Hello"}
