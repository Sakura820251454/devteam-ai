import asyncio
import hashlib
from typing import List, Optional, Dict, Any, AsyncIterator
from app.core.config import get_settings
from app.core.llm import Message, LLMResponse
from app.core.llm_providers import LLMProviderFactory, BaseLLMProvider
from app.core.llm_models import LLMProviderType, calculate_cost, get_model_info, AVAILABLE_MODELS
from app.models.agent import Agent, LLMConfig
from app.services.llm.cost_tracker import cost_tracker


class LLMService:
    def __init__(self):
        self.settings = get_settings()
        self._provider_cache: Dict[str, BaseLLMProvider] = {}
        self._lock = asyncio.Lock()
        self._cost_records: List[Dict[str, Any]] = []

    def _get_provider_key(self, provider: LLMProviderType, agent_id: Optional[str] = None) -> str:
        return f"{provider.value}:{agent_id or 'default'}"

    async def _get_provider(
        self,
        llm_config: Optional[LLMConfig] = None,
        agent_id: Optional[str] = None
    ) -> BaseLLMProvider:
        if llm_config:
            provider_type = LLMProviderType(llm_config.provider)
            model = llm_config.model
        else:
            provider_type = LLMProviderType(self.settings.default_llm_provider)
            model = self.settings.default_llm_model
        
        cache_key = self._get_provider_key(provider_type, agent_id)
        
        async with self._lock:
            if cache_key not in self._provider_cache:
                provider = LLMProviderFactory.get_provider(provider_type)
                self._provider_cache[cache_key] = provider
            
            return self._provider_cache[cache_key]

    async def chat(
        self,
        messages: List[Message],
        agent: Optional[Agent] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        track_cost: bool = True,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        llm_config = agent.config.llm_config if agent else None

        if model is None and llm_config:
            model = llm_config.model
        elif model is None:
            model = self.settings.default_llm_model

        if temperature is None:
            if llm_config:
                temperature = llm_config.temperature
            else:
                temperature = 0.7

        if max_tokens is None and llm_config:
            max_tokens = llm_config.max_tokens

        provider = await self._get_provider(llm_config, agent.id if agent else None)

        effective_timeout = timeout or 120.0

        try:
            response = await asyncio.wait_for(
                provider.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    cancellation_token=cancellation_token,
                    tools=tools,
                ),
                timeout=effective_timeout + 10.0
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM call timed out after {effective_timeout}s")
        
        if track_cost:
            prompt_tokens = response.usage.get("prompt_tokens", 0)
            completion_tokens = response.usage.get("completion_tokens", 0)
            await cost_tracker.record_cost(
                agent_id=agent.id if agent else None,
                task_id=task_id,
                model=model,
                provider=llm_config.provider if llm_config else self.settings.default_llm_provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
            self._record_cost(
                agent_id=agent.id if agent else None,
                task_id=task_id,
                model=model,
                usage=response.usage,
                provider_type=llm_config.provider if llm_config else self.settings.default_llm_provider
            )
        
        return response

    async def stream_chat(
        self,
        messages: List[Message],
        agent: Optional[Agent] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> AsyncIterator[str]:
        llm_config = agent.config.llm_config if agent else None

        if model is None and llm_config:
            model = llm_config.model
        elif model is None:
            model = self.settings.default_llm_model

        if temperature is None:
            if llm_config:
                temperature = llm_config.temperature
            else:
                temperature = 0.7

        if max_tokens is None and llm_config:
            max_tokens = llm_config.max_tokens

        provider = await self._get_provider(llm_config, agent.id if agent else None)

        full_response = ""
        async for chunk in provider.stream_chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            cancellation_token=cancellation_token
        ):
            full_response += chunk
            yield chunk
        
        if full_response:
            estimated_tokens = len(full_response) // 4
            self._record_cost(
                agent_id=agent.id if agent else None,
                task_id=task_id,
                model=model,
                usage={
                    "prompt_tokens": sum(len(m.content) // 4 for m in messages),
                    "completion_tokens": estimated_tokens,
                    "total_tokens": sum(len(m.content) // 4 for m in messages) + estimated_tokens
                },
                provider_type=llm_config.provider if llm_config else self.settings.default_llm_provider
            )

    def _record_cost(
        self,
        agent_id: Optional[str],
        task_id: Optional[str],
        model: str,
        usage: Dict[str, int],
        provider_type: str
    ):
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        
        cost = calculate_cost(model, prompt_tokens, completion_tokens)
        
        record = {
            "agent_id": agent_id,
            "task_id": task_id,
            "model": model,
            "provider": provider_type,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost
        }
        
        self._cost_records.append(record)

    def get_cost_records(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        records = self._cost_records
        
        if agent_id:
            records = [r for r in records if r["agent_id"] == agent_id]
        
        if task_id:
            records = [r for r in records if r["task_id"] == task_id]
        
        return records[-limit:]

    def get_cost_summary(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        records = self.get_cost_records(agent_id, task_id, limit=10000)
        
        if not records:
            return {
                "total_cost": 0.0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "call_count": 0,
                "by_model": {},
                "by_agent": {}
            }
        
        total_cost = sum(r["cost"] for r in records)
        total_tokens = sum(r["total_tokens"] for r in records)
        prompt_tokens = sum(r["prompt_tokens"] for r in records)
        completion_tokens = sum(r["completion_tokens"] for r in records)
        
        by_model: Dict[str, Dict[str, Any]] = {}
        by_agent: Dict[str, Dict[str, Any]] = {}
        
        for r in records:
            model = r["model"]
            if model not in by_model:
                by_model[model] = {"cost": 0.0, "tokens": 0, "calls": 0}
            by_model[model]["cost"] += r["cost"]
            by_model[model]["tokens"] += r["total_tokens"]
            by_model[model]["calls"] += 1
            
            agent = r["agent_id"] or "unknown"
            if agent not in by_agent:
                by_agent[agent] = {"cost": 0.0, "tokens": 0, "calls": 0}
            by_agent[agent]["cost"] += r["cost"]
            by_agent[agent]["tokens"] += r["total_tokens"]
            by_agent[agent]["calls"] += 1
        
        return {
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "call_count": len(records),
            "by_model": {k: {kk: round(vv, 6) if kk == "cost" else vv for kk, vv in v.items()} for k, v in by_model.items()},
            "by_agent": {k: {kk: round(vv, 6) if kk == "cost" else vv for kk, vv in v.items()} for k, v in by_agent.items()}
        }

    def clear_cost_records(self):
        self._cost_records.clear()

    @staticmethod
    def get_available_models() -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "provider": model.provider.value,
                "input_cost_per_1k": model.input_cost_per_1k,
                "output_cost_per_1k": model.output_cost_per_1k,
                "max_tokens": model.max_tokens,
                "supports_streaming": model.supports_streaming,
                "description": model.description
            }
            for name, model in AVAILABLE_MODELS.items()
        }

    @staticmethod
    def get_available_providers() -> List[str]:
        return [p.value for p in LLMProviderType]


llm_service = LLMService()
