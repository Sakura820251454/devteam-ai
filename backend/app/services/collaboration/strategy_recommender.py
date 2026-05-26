"""策略推荐服务 — LLM 根据项目需求和 Agent 组合推荐协作策略"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from app.core.llm import Message as LLMMessage
from app.services.shared.prompt_registry import registry

logger = logging.getLogger(__name__)


@dataclass
class StrategyRecommendation:
    recommended_strategy: str  # "sequential" | "hierarchical" | "discussion"
    confidence: float  # 0.0 - 1.0
    reasoning: str
    suggested_coordinator: Optional[str] = None
    alternative_strategies: List[Dict[str, Any]] = field(default_factory=list)


class StrategyRecommender:
    """LLM 策略推荐器"""

    async def recommend(
        self,
        project_name: str,
        project_description: str,
        requirements: str,
        agent_ids: List[str],
        template_id: Optional[str] = None,
    ) -> StrategyRecommendation:
        """根据项目信息 + agent 组合推荐协作策略"""
        from app.services.agent.agent_service import agent_service
        from app.services.agent.agent_trait_service import agent_trait_service

        # 确保 traits 已生成
        await agent_trait_service.ensure_traits_batch(agent_ids)

        # 构建 agent 信息表
        agent_rows = []
        for aid in agent_ids:
            agent = agent_service.get_agent(aid)
            traits = agent_trait_service.get_trait(aid)
            if agent:
                name = agent.get('name', aid)
                summary = traits.summary if traits else agent.get("description", "")
                skills_text = f"能力：{', '.join(traits.skills)}" if traits and traits.skills else ""
                agent_rows.append(
                    f"- {aid}: {name} — {summary}。{skills_text}"
                )

        agents_text = "\n".join(agent_rows) if agent_rows else "（无 agent 信息）"

        prompt = registry.render("collaboration.strategy_recommender.recommend", {
            "project_name": project_name,
            "project_description": project_description,
            "requirements": requirements or project_description,
            "agents_text": agents_text,
        })

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(
                            role="system",
                            content=registry.render("collaboration.strategy_recommender.system", {}),
                        ),
                        LLMMessage(role="user", content=prompt),
                    ],
                    track_cost=False,
                    timeout=20.0,
                ),
                timeout=30.0,
            )

            data = self._parse_json(response.content)
            return StrategyRecommendation(
                recommended_strategy=data.get("recommended_strategy", "sequential"),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                suggested_coordinator=data.get("suggested_coordinator"),
                alternative_strategies=data.get("alternative_strategies", []),
            )
        except Exception as e:
            logger.warning(f"Strategy recommendation failed: {e}")
            return StrategyRecommendation(
                recommended_strategy="sequential",
                confidence=0.3,
                reasoning=f"推荐失败 ({e})，默认使用顺序执行策略",
            )

    def _parse_json(self, text: str) -> dict:
        import re

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}


strategy_recommender = StrategyRecommender()
