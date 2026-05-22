"""Agent 特质服务 — 用 LLM 从 soul.md 生成结构化能力画像，用于任务匹配"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.core.llm import Message as LLMMessage

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

        prompt = f"""你是一位人力资源分析专家。请根据以下 Agent 的灵魂定义，提取结构化的能力特征。

Agent 名称: {agent.get('name', agent_id)}

## 核心原则 (Core Principles)
{principles or '无'}

## 执行规则 (Execution Rules)
{rules or '无'}

请严格按以下 JSON 格式输出（不要输出其他内容）:
{{
  "role_label": "该Agent最适合的中文角色标签（如：架构师/后端开发/前端开发/测试工程师/运维工程师/产品经理）",
  "skills": ["具体技能1", "具体技能2", "具体技能3"],
  "strength_areas": ["擅长领域1", "擅长领域2"],
  "collaboration_style": "分析型/务实型/主动型/严谨型",
  "communication_style": "简洁型/详细型",
  "summary": "一句话总结该Agent的特点和最擅长的任务类型"
}}"""

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(role="system", content="你是一位人力资源分析专家。只输出 JSON。"),
                        LLMMessage(role="user", content=prompt),
                    ],
                    track_cost=False,
                    timeout=20.0,
                ),
                timeout=30.0,
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
