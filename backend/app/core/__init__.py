from app.core.config import get_settings, Settings, LLMMode
from app.core.llm import LLMProvider, Message, LLMResponse
from app.core.mock_llm import MockLLMProvider


async def create_llm_provider() -> LLMProvider | MockLLMProvider:
    """根据配置创建 LLM Provider"""
    settings = get_settings()
    
    if settings.llm_mode == LLMMode.MOCK:
        provider = MockLLMProvider()
        await provider.__aenter__()
        return provider
    else:
        provider = LLMProvider()
        await provider.__aenter__()
        return provider


__all__ = [
    "get_settings",
    "Settings",
    "LLMMode",
    "LLMProvider",
    "Message",
    "LLMResponse",
    "MockLLMProvider",
    "create_llm_provider",
]
