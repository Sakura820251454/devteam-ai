import httpx
import json
from typing import AsyncIterator, Optional, List, Dict, Any
from app.core.config import get_settings


class Message:
    """LLM 对话消息，兼容 OpenAI tool calling 格式"""

    def __init__(
        self,
        role: str,
        content: str = "",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role}
        if self.content:
            d["content"] = self.content
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d

    @classmethod
    def tool_result(cls, tool_call_id: str, name: str, content: str) -> "Message":
        """创建 tool 角色消息（工具执行结果）"""
        return cls(role="tool", content=content, tool_call_id=tool_call_id, name=name)


class LLMResponse:
    content: Optional[str]
    tool_calls: Optional[List[Dict[str, Any]]]
    usage: Dict[str, int]
    model: str
    finish_reason: str

    def __init__(
        self,
        content: Optional[str],
        usage: Dict[str, int],
        model: str,
        finish_reason: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ):
        self.content = content
        self.usage = usage
        self.model = model
        self.finish_reason = finish_reason
        self.tool_calls = tool_calls


class LLMProvider:
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.settings.deepseek_base_url,
            headers={
                "Authorization": f"Bearer {self.settings.deepseek_api_key}",
                "Content-Type": "application/json"
            },
            timeout=self.settings.request_timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        model = model or self.settings.deepseek_model

        payload = {
            "model": model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()

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
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        model = model or self.settings.deepseek_model

        payload = {
            "model": model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]


async def create_llm_provider() -> LLMProvider:
    provider = LLMProvider()
    await provider.__aenter__()
    return provider
