"""Soul 匹配服务 — Step 4: 将建议的角色匹配到 soul 池中的最佳人格"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.services.team.team_suggester import SuggestedRole, TeamSuggestion

logger = logging.getLogger(__name__)


@dataclass
class SoulMatch:
    role_name: str
    soul_id: str
    soul_name: str
    role_responsibilities: str
    confidence: float
    match_reason: str


@dataclass
class TeamFormation:
    project_id: str
    matches: List[SoulMatch]
    strategy: str
    strategy_reasoning: str
    coordinator_id: Optional[str] = None


class SoulMatcher:
    """将LLM建议的角色匹配到soul池中的agent实例"""

    def match_roles_to_souls(
        self,
        suggestion: TeamSuggestion,
    ) -> List[SoulMatch]:
        """将建议的角色匹配到 soul 池。

        匹配策略（按优先级）:
        1. suggested_soul 非空 → 按名称精确匹配
        2. suggested_soul 非空 → 按名称模糊匹配（包含关系）
        3. 兜底 → 返回空匹配，由调用方决定
        """
        from app.services.agent.agent_service import agent_service

        soul_agents = agent_service.get_soul_based_agents()
        if not soul_agents:
            logger.warning("No soul-based agents available for matching")
            return []

        matches = []
        used_souls: set = set()

        for role in suggestion.roles:
            match = self._find_best_match(role, soul_agents, used_souls)
            if match:
                used_souls.add(match.soul_id)
                matches.append(match)
            else:
                # 如果所有 soul 都被占用，尝试复用
                logger.warning(f"No available soul found for role '{role.role_name}'")

        return matches

    def _find_best_match(
        self,
        role: SuggestedRole,
        soul_agents: List[Dict],
        used_souls: set,
    ) -> Optional[SoulMatch]:
        # Step 1: 精确匹配 suggested_soul
        if role.suggested_soul:
            target_name = role.suggested_soul.strip()
            for agent in soul_agents:
                agent_name = agent.get("name", "")
                if agent_name == target_name and agent["id"] not in used_souls:
                    return SoulMatch(
                        role_name=role.role_name,
                        soul_id=agent["id"],
                        soul_name=agent_name,
                        role_responsibilities=role.responsibilities,
                        confidence=0.9,
                        match_reason=role.matching_reason or f"LLM建议 {target_name} 担任此角色",
                    )

        # Step 2: 模糊匹配（名称包含关系）
        if role.suggested_soul:
            target_lower = role.suggested_soul.strip().lower()
            for agent in soul_agents:
                agent_name = agent.get("name", "")
                agent_id = agent["id"]
                if (
                    target_lower in agent_name.lower() or agent_name.lower() in target_lower
                ) and agent_id not in used_souls:
                    return SoulMatch(
                        role_name=role.role_name,
                        soul_id=agent_id,
                        soul_name=agent_name,
                        role_responsibilities=role.responsibilities,
                        confidence=0.7,
                        match_reason=role.matching_reason or f"模糊匹配: {agent_name} ≈ {role.suggested_soul}",
                    )

        # Step 3: 兜底 — 选第一个未使用的 soul
        for agent in soul_agents:
            if agent["id"] not in used_souls:
                return SoulMatch(
                    role_name=role.role_name,
                    soul_id=agent["id"],
                    soul_name=agent.get("name", ""),
                    role_responsibilities=role.responsibilities,
                    confidence=0.4,
                    match_reason="无建议匹配，使用第一个可用人格",
                )

        return None

    def create_team_instances(
        self,
        project_id: str,
        matches: List[SoulMatch],
        strategy: str,
    ) -> TeamFormation:
        """生成团队实例：绑定 agent 到项目"""
        from app.services.agent.agent_service import agent_service

        formation = TeamFormation(
            project_id=project_id,
            matches=matches,
            strategy=strategy,
            strategy_reasoning="",
        )

        for match in matches:
            try:
                agent_service.assign_agent_to_project(match.soul_id, project_id)
                logger.info(f"Assigned {match.soul_name} ({match.soul_id}) → {match.role_name} in {project_id}")
            except Exception as e:
                logger.warning(f"Failed to assign {match.soul_id}: {e}")

        if matches and strategy == "hierarchical":
            formation.coordinator_id = matches[0].soul_id

        return formation


soul_matcher = SoulMatcher()
