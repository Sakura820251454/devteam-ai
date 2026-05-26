"""Agent 特质服务 — 用 LLM 从 soul.md 生成结构化能力画像，用于任务匹配"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.core.llm import Message as LLMMessage
from app.services.shared.prompt_registry import registry

logger = logging.getLogger(__name__)


@dataclass
class AgentTraits:
    agent_id: str
    role_label: str  # "架构师", "后端开发" etc.
    skills: List[str]
    strength_areas: List[str]
    collaboration_style: str  # "分析型", "务实型", "主动型", "严谨型"
    communication_style: str  # "简洁型", "详细型"
    summary: str


class AgentTraitService:
    """用 LLM 一次性为 agent 生成能力画像，缓存复用"""

    def __init__(self):
        self._traits: Dict[str, AgentTraits] = {}
        self._lock = asyncio.Lock()

    def get_trait(self, agent_id: str) -> Optional[AgentTraits]:
        return self._traits.get(agent_id)

    def has_traits(self, agent_id: str) -> bool:
        return agent_id in self._traits

    async def ensure_traits(self, agent_id: str) -> AgentTraits:
        """获取或生成 agent 特质（幂等）"""
        if agent_id in self._traits:
            return self._traits[agent_id]

        async with self._lock:
            if agent_id in self._traits:
                return self._traits[agent_id]
            traits = await self._generate_trait(agent_id)
            self._traits[agent_id] = traits
            return traits

    async def ensure_traits_batch(self, agent_ids: List[str]) -> Dict[str, AgentTraits]:
        """批量确保特质已生成"""
        missing = [aid for aid in agent_ids if aid not in self._traits]
        if missing:
            results = await asyncio.gather(
                *[self._generate_trait(aid) for aid in missing],
                return_exceptions=True,
            )
            async with self._lock:
                for agent_id, result in zip(missing, results):
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to generate traits for {agent_id}: {result}")
                        self._traits[agent_id] = self._fallback_traits(agent_id)
                    else:
                        self._traits[agent_id] = result
        return {aid: self._traits.get(aid) for aid in agent_ids if aid in self._traits}

    async def _generate_trait(self, agent_id: str) -> AgentTraits:
        from app.services.agent.agent_service import agent_service

        agent = agent_service.get_agent(agent_id)
        if not agent:
            return self._fallback_traits(agent_id)

        soul_data = agent.get("soul_data")
        if not soul_data:
            return self._fallback_traits(agent_id)

        principles = "\n".join(f"- {p}" for p in soul_data.get("core_principles", []))
        rules = "\n".join(f"- {r}" for r in soul_data.get("execution_rules", []))

        prompt = registry.render("agent.trait.generate", {
            "agent_name": agent.get("name", agent_id),
            "principles": principles or "无",
            "rules": rules or "无",
        })

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(role="system", content=registry.render("agent.trait.generate_system", {})),
                        LLMMessage(role="user", content=prompt),
                    ],
                    track_cost=False,
                    timeout=45.0,
                ),
                timeout=55.0,
            )

            data = self._parse_trait_json(response.content)
            return AgentTraits(
                agent_id=agent_id,
                role_label=data.get("role_label", agent.get("name", agent_id)),
                skills=data.get("skills", []),
                strength_areas=data.get("strength_areas", []),
                collaboration_style=data.get("collaboration_style", "务实型"),
                communication_style=data.get("communication_style", "简洁型"),
                summary=data.get("summary", f"{agent.get('name', agent_id)} 的核心能力"),
            )
        except Exception as e:
            logger.warning(f"Trait generation for {agent_id} failed: {e}")
            return self._fallback_traits(agent_id)

    def _parse_trait_json(self, text: str) -> dict:
        import re

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}

    def _fallback_traits(self, agent_id: str) -> AgentTraits:
        from app.services.agent.agent_service import agent_service

        agent = agent_service.get_agent(agent_id)
        role_label = agent.get("name", agent_id) if agent else agent_id
        return AgentTraits(
            agent_id=agent_id,
            role_label=role_label,
            skills=[],
            strength_areas=[],
            collaboration_style="务实型",
            communication_style="简洁型",
            summary=f"{agent.get('name', agent_id) if agent else agent_id}: {role_label}",
        )

    async def build_soul_pool_text(self) -> str:
        """构建可用于团队建议 prompt 的人格库文本。

        优先使用已缓存的特质，未缓存则用 fallback 并触发后台预热，
        避免串行 LLM 调用阻塞团队建议 API 响应。
        """
        from app.services.agent.agent_service import agent_service

        soul_agents = agent_service.get_soul_based_agents()
        if not soul_agents:
            return "（暂无可用人格库）"

        uncached_ids = [
            agent.get("id", "")
            for agent in soul_agents
            if agent.get("id", "") and not self.has_traits(agent.get("id", ""))
        ]
        if uncached_ids:
            asyncio.create_task(self._background_warmup(uncached_ids))

        rows = []
        for agent in soul_agents:
            aid = agent.get("id", "")
            name = agent.get("name", aid)
            traits = self.get_trait(aid) or self._fallback_traits(aid)

            principles = agent.get("soul_data", {}).get("core_principles", []) if agent.get("soul_data") else []

            rows.append(
                f"## {name}\n"
                f"- 协作风格: {traits.collaboration_style}\n"
                f"- 沟通风格: {traits.communication_style}\n"
                f"- 核心原则: {'; '.join(principles[:3]) if principles else '未定义'}\n"
                f"- 擅长领域: {', '.join(traits.strength_areas[:3]) if traits.strength_areas else '通用'}\n"
                f"- 能力摘要: {traits.summary}"
            )

        return "\n\n".join(rows) if rows else "（暂无可用人格库）"

    async def _background_warmup(self, agent_ids: List[str]):
        """后台预热特质缓存，不阻塞主流程。"""
        try:
            await self.ensure_traits_batch(agent_ids)
            logger.info(f"Background trait warmup completed for {len(agent_ids)} agents")
        except Exception as e:
            logger.warning(f"Background trait warmup failed: {e}")

    async def match_task_to_agent(
        self,
        required_skills: List[str],
        agent_ids: List[str],
    ) -> List[Tuple[str, float]]:
        """按技能交集匹配 agent，返回 (agent_id, score) 降序排列"""
        if not required_skills:
            return [(aid, 0.0) for aid in agent_ids]

        await self.ensure_traits_batch(agent_ids)

        scores = []
        for agent_id in agent_ids:
            traits = self._traits.get(agent_id)
            if not traits or not traits.skills:
                scores.append((agent_id, 0.0))
                continue

            agent_skills_lower = {s.lower() for s in traits.skills}
            required_lower = {s.lower() for s in required_skills}
            intersection = agent_skills_lower & required_lower
            union = agent_skills_lower | required_lower
            score = len(intersection) / len(union) if union else 0.0
            scores.append((agent_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


agent_trait_service = AgentTraitService()
