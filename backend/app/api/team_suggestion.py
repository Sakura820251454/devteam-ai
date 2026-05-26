"""团队建议 API — Step 3 + Step 4"""

import dataclasses
from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.task.task_analyzer import task_analyzer
from app.services.team.team_suggester import team_suggester
from app.services.team.soul_matcher import soul_matcher

router = APIRouter(prefix="/api/team-suggestion", tags=["团队建议"])


class SuggestTeamRequest(BaseModel):
    task_description: str


@router.post("/")
async def suggest_team(request: SuggestTeamRequest):
    """Step 2+3: 分析任务 + 建议团队角色和策略"""
    analysis = await task_analyzer.analyze(request.task_description)
    suggestion = await team_suggester.suggest(analysis)
    return {
        "analysis": dataclasses.asdict(analysis),
        "suggestion": dataclasses.asdict(suggestion),
    }


class GenerateTeamRequest(BaseModel):
    project_id: str
    roles: List[Dict]
    strategy: str


@router.post("/generate")
async def generate_team(request: GenerateTeamRequest):
    """Step 4: 将确认的角色匹配到 soul 并生成团队实例"""
    from app.services.team.team_suggester import SuggestedRole, TeamSuggestion, StrategySuggestion

    roles = [
        SuggestedRole(
            role_name=r.get("role_name", ""),
            responsibilities=r.get("responsibilities", ""),
            required_capabilities=r.get("required_capabilities", []),
            suggested_soul=r.get("suggested_soul", ""),
            matching_reason=r.get("matching_reason", ""),
            priority=r.get("priority", "recommended"),
        )
        for r in request.roles
    ]

    suggestion = TeamSuggestion(
        roles=roles,
        strategy=StrategySuggestion(recommended=request.strategy),
    )

    matches = soul_matcher.match_roles_to_souls(suggestion)
    formation = soul_matcher.create_team_instances(
        project_id=request.project_id,
        matches=matches,
        strategy=request.strategy,
    )

    assign_result = [
        {
            "role_name": m.role_name,
            "soul_id": m.soul_id,
            "soul_name": m.soul_name,
            "confidence": m.confidence,
        }
        for m in matches
    ]

    return {
        "project_id": formation.project_id,
        "strategy": formation.strategy,
        "coordinator_id": formation.coordinator_id,
        "assignments": assign_result,
    }
