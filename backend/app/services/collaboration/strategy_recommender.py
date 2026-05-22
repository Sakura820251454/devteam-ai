"""策略推荐服务 — LLM 根据项目需求和 Agent 组合推荐协作策略"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from app.core.llm import Message as LLMMessage

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
                role = traits.role_label if traits else agent.get("type", "未知")
                summary = traits.summary if traits else agent.get("description", "")
                agent_rows.append(
                    f"- {aid}: {agent.get('name', aid)} ({role}) — {summary}"
                )

        agents_text = "\n".join(agent_rows) if agent_rows else "（无 agent 信息）"

        prompt = f"""你是一个项目管理专家。请根据以下信息，推荐最适合的团队协作策略。

## 项目信息
- 名称: {project_name}
- 描述: {project_description}
- 需求: {requirements or project_description}

## 可用团队成员
{agents_text}

## 可选策略
1. **sequential** (顺序执行): 适合 1-2 人的简单任务，按阶段顺序执行，一人负责一个阶段
2. **hierarchical** (层级委派): 适合 3+ 人的复杂项目，协调者拆解委派给工人执行，最后汇总
3. **discussion** (圆桌讨论): 适合需要多视角碰撞的决策场景，Agent 集体讨论达成共识

## 分析要求
- 考虑团队规模和角色覆盖
- 考虑项目复杂度和任务类型
- 考虑是否需要多视角（如技术选型、架构设计）

## 输出格式 (JSON)
{{
  "recommended_strategy": "sequential|hierarchical|discussion",
  "confidence": 0.85,
  "reasoning": "详细分析说明",
  "suggested_coordinator": "agent_id 或 null (仅 hierarchical 需要)",
  "alternative_strategies": [
    {{"strategy": "sequential", "reason": "如果X的话也可以考虑..."}}
  ]
}}"""

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(
                            role="system",
                            content="你是一位项目管理专家。只输出 JSON。",
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
