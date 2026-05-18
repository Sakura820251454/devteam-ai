import httpx
import json
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List, Dict, Any
from app.core.config import get_settings
from app.core.llm import Message, LLMResponse
from app.core.llm_models import (
    LLMProviderType,
    get_model_info,
    AVAILABLE_MODELS,
    LLMModelInfo
)


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> AsyncIterator[str]:
        pass


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=120
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> LLMResponse:
        model = model or "gpt-4o-mini"

        payload = {
            "model": model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with asyncio.timeout(timeout):
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            if cancellation_token and cancellation_token.is_set():
                raise asyncio.CancelledError("LLM call cancelled")

            data = response.json()
            choice = data["choices"][0]

            return LLMResponse(
                content=choice["message"]["content"],
                usage=data.get("usage", {}),
                model=data.get("model", model),
                finish_reason=choice.get("finish_reason", "stop")
            )

    async def stream_chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> AsyncIterator[str]:
        model = model or "gpt-4o-mini"

        payload = {
            "model": model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with asyncio.timeout(timeout):
            async with self.client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token and cancellation_token.is_set():
                        raise asyncio.CancelledError("LLM stream cancelled")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]


class DeepSeekProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=120
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> LLMResponse:
        model = model or "deepseek-chat"

        payload = {
            "model": model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with asyncio.timeout(timeout):
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            if cancellation_token and cancellation_token.is_set():
                raise asyncio.CancelledError("LLM call cancelled")

            data = response.json()
            choice = data["choices"][0]

            return LLMResponse(
                content=choice["message"]["content"],
                usage=data.get("usage", {}),
                model=data.get("model", model),
                finish_reason=choice.get("finish_reason", "stop")
            )

    async def stream_chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> AsyncIterator[str]:
        model = model or "deepseek-chat"

        payload = {
            "model": model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with asyncio.timeout(timeout):
            async with self.client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token and cancellation_token.is_set():
                        raise asyncio.CancelledError("LLM stream cancelled")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            timeout=120
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> LLMResponse:
        model = model or "claude-3-5-sonnet-20240620"
        max_tokens = max_tokens or 4096

        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        payload = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_msg:
            payload["system"] = system_msg

        async with asyncio.timeout(timeout):
            response = await self.client.post("/v1/messages", json=payload)
            response.raise_for_status()

            if cancellation_token and cancellation_token.is_set():
                raise asyncio.CancelledError("LLM call cancelled")

            data = response.json()

            return LLMResponse(
                content=data["content"][0]["text"],
                usage={
                    "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                },
                model=model,
                finish_reason=data.get("stop_reason", "end_turn")
            )

    async def stream_chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> AsyncIterator[str]:
        model = model or "claude-3-5-sonnet-20240620"
        max_tokens = max_tokens or 4096

        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        payload = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if system_msg:
            payload["system"] = system_msg

        async with asyncio.timeout(timeout):
            async with self.client.stream("POST", "/v1/messages", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token and cancellation_token.is_set():
                        raise asyncio.CancelledError("LLM stream cancelled")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")


class AzureOpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-02-15-preview"):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.api_version = api_version
        self.client = httpx.AsyncClient(
            base_url=self.endpoint,
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json"
            },
            timeout=120
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> LLMResponse:
        deployment_name = model or "gpt-4o-mini"

        payload = {
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        url = f"/openai/deployments/{deployment_name}/chat/completions?api-version={self.api_version}"

        async with asyncio.timeout(timeout):
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            if cancellation_token and cancellation_token.is_set():
                raise asyncio.CancelledError("LLM call cancelled")

            data = response.json()
            choice = data["choices"][0]

            return LLMResponse(
                content=choice["message"]["content"],
                usage=data.get("usage", {}),
                model=data.get("model", deployment_name),
                finish_reason=choice.get("finish_reason", "stop")
            )

    async def stream_chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> AsyncIterator[str]:
        deployment_name = model or "gpt-4o-mini"

        payload = {
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        url = f"/openai/deployments/{deployment_name}/chat/completions?api-version={self.api_version}"

        async with asyncio.timeout(timeout):
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token and cancellation_token.is_set():
                        raise asyncio.CancelledError("LLM stream cancelled")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]


class LLMProviderFactory:
    _instance = None
    _providers: Dict[LLMProviderType, type] = {
        LLMProviderType.OPENAI: OpenAIProvider,
        LLMProviderType.DEEPSEEK: DeepSeekProvider,
        LLMProviderType.ANTHROPIC: AnthropicProvider,
        LLMProviderType.AZURE: AzureOpenAIProvider,
    }

    @classmethod
    def get_provider(
        cls,
        provider_type: LLMProviderType,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: Optional[str] = None
    ) -> BaseLLMProvider:
        if provider_type == LLMProviderType.MOCK:
            from app.core.mock_llm import MockLLMProvider
            return MockLLMProvider()
        
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {provider_type}")
        
        settings = get_settings()
        
        if provider_type == LLMProviderType.OPENAI:
            key = api_key or settings.openai_api_key
            url = base_url or settings.openai_base_url
            return provider_class(key, url)
        
        elif provider_type == LLMProviderType.DEEPSEEK:
            key = api_key or settings.deepseek_api_key
            url = base_url or settings.deepseek_base_url
            return provider_class(key, url)
        
        elif provider_type == LLMProviderType.ANTHROPIC:
            key = api_key or settings.anthropic_api_key
            url = base_url or settings.anthropic_base_url
            return provider_class(key, url)
        
        elif provider_type == LLMProviderType.AZURE:
            key = api_key or settings.azure_api_key
            ep = endpoint or settings.azure_endpoint
            ver = api_version or settings.azure_api_version
            return provider_class(key, ep, ver)
        
        raise ValueError(f"Unsupported provider: {provider_type}")

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> BaseLLMProvider:
        provider_type = LLMProviderType(config.get("provider", "mock"))
        return cls.get_provider(
            provider_type=provider_type,
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            endpoint=config.get("endpoint"),
            api_version=config.get("api_version")
        )

    @classmethod
    def get_available_providers(cls) -> List[str]:
        return [p.value for p in LLMProviderType]

    @classmethod
    def get_models_by_provider(cls, provider: LLMProviderType) -> List[LLMModelInfo]:
        return [m for m in AVAILABLE_MODELS.values() if m.provider == provider]

    @classmethod
    def get_all_models(cls) -> Dict[str, LLMModelInfo]:
        return AVAILABLE_MODELS.copy()
