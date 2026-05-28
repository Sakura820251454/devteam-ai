"""团队组建建议服务 — Step 3: 基于任务分析建议角色+策略"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.llm import Message as LLMMessage
from app.services.shared.prompt_registry import registry
from app.services.task.task_analyzer import TaskAnalysis
from app.services.shared.json_extractor import extract_and_validate, JSONExtractionError, JSONValidationError
from app.services.shared.validation import TeamSuggestionResult

logger = logging.getLogger(__name__)


@dataclass
class SuggestedRole:
    role_name: str
    responsibilities: str
    required_capabilities: List[str] = field(default_factory=list)
    suggested_soul: str = ""
    matching_reason: str = ""
    priority: str = "recommended"


@dataclass
class StrategySuggestion:
    recommended: str = "sequential"
    reasoning: str = ""
    alternatives: List[dict] = field(default_factory=list)


@dataclass
class TeamSuggestion:
    team_name: str = ""
    roles: List[SuggestedRole] = field(default_factory=list)
    strategy: Optional[StrategySuggestion] = None
    overall_rationale: str = ""


class TeamSuggester:
    """LLM 团队组建建议器"""

    async def suggest(self, analysis: TaskAnalysis) -> TeamSuggestion:
        from app.services.agent.agent_trait_service import agent_trait_service

        soul_pool_text = await agent_trait_service.build_soul_pool_text()
        breakdown_text = ", ".join(analysis.breakdown) if analysis.breakdown else "未指定"

        prompt = registry.render("team.build_suggestion", {
            "domain": analysis.domain,
            "task_type": analysis.task_type,
            "complexity": analysis.complexity,
            "breakdown": breakdown_text,
            "key_challenge": analysis.key_challenge,
            "soul_pool_text": soul_pool_text,
        })

        try:
            from app.services.llm.llm_service import llm_service

            response = await asyncio.wait_for(
                llm_service.chat(
                    messages=[
                        LLMMessage(
                            role="system",
                            content=registry.render("team.build_suggestion_system", {}),
                        ),
                        LLMMessage(role="user", content=prompt),
                    ],
                    track_cost=False,
                    timeout=45.0,
                ),
                timeout=55.0,
            )

            return self._parse_suggestion(response.content)
        except Exception as e:
            logger.warning(f"Team suggestion failed: {e}")
            return TeamSuggestion(
                team_name="默认团队",
                strategy=StrategySuggestion(recommended="sequential", reasoning=f"建议失败 ({e})，默认使用顺序执行"),
                overall_rationale="团队建议生成失败，请手动配置团队。",
            )

    def _parse_suggestion(self, text: str) -> TeamSuggestion:
        try:
            data = extract_and_validate(text, TeamSuggestionResult)
            roles = [SuggestedRole(
                role_name=r.role_name,
                responsibilities=r.responsibilities,
                required_capabilities=r.required_capabilities,
                suggested_soul=r.suggested_soul,
                matching_reason=r.matching_reason,
                priority=r.priority,
            ) for r in data.roles]
            strategy = StrategySuggestion(
                recommended=data.strategy.recommended,
                reasoning=data.strategy.reasoning,
                alternatives=[a.model_dump() if hasattr(a, 'model_dump') else a for a in data.strategy.alternatives],
            )
            return TeamSuggestion(
                team_name=data.team_name,
                roles=roles,
                strategy=strategy,
                overall_rationale=data.overall_rationale,
            )
        except (JSONExtractionError, JSONValidationError) as e:
            logger.warning(f"团队建议 JSON 解析失败: {e}")
            return TeamSuggestion()


team_suggester = TeamSuggester()
