"""
技能推荐 API - Phase 4 优化

提供技能管理和推荐的 REST API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.learning.intelligent_learning import get_learning_service, IntelligentLearningService
from app.services.learning.skill_manager import Skill
from app.services.learning.matcher import SkillMatch


router = APIRouter(prefix="/api/skills", tags=["技能管理"])


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    trigger_keywords: List[str]
    implementation: Dict[str, Any]
    success_rate: float
    usage_count: int


class SkillMatchResponse(BaseModel):
    skill: SkillResponse
    score: float
    match_type: str
    confidence: float


class RecommendRequest(BaseModel):
    task_description: str
    agent_id: Optional[str] = None
    max_results: int = 5


class LearnRequest(BaseModel):
    agent_id: str
    task_description: str
    decisions: List[Dict[str, str]]
    outcomes: Dict[str, Any]
    success: str = "success"
    session_id: Optional[str] = None
    task_id: Optional[str] = None


class LearningStatsResponse(BaseModel):
    total_trajectories: int
    successful_trajectories: int
    success_rate: float
    total_skills: int
    skills_by_category: Dict[str, Any]


@router.get("/", response_model=List[SkillResponse])
async def list_skills(
    category: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取技能列表"""
    service = await get_learning_service(db)
    
    if category:
        skills = await service.get_skills_by_category(category, limit)
    else:
        skills = await service.skill_manager.get_all_skills(limit)
    
    return [
        SkillResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            category=s.category,
            trigger_keywords=s.trigger_keywords,
            implementation=s.implementation,
            success_rate=s.success_rate,
            usage_count=s.usage_count,
        )
        for s in skills
    ]


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取单个技能详情"""
    service = await get_learning_service(db)
    skill = await service.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        category=skill.category,
        trigger_keywords=skill.trigger_keywords,
        implementation=skill.implementation,
        success_rate=skill.success_rate,
        usage_count=skill.usage_count,
    )


@router.post("/recommend", response_model=List[SkillMatchResponse])
async def recommend_skills(
    request: RecommendRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    智能推荐相关技能
    
    根据任务描述匹配最相关的技能
    - 优先匹配指定 Agent 的技能
    - 综合考虑关键词匹配和语义相似度
    """
    service = await get_learning_service(db)
    
    matches = await service.recommend_skills(
        task_description=request.task_description,
        agent_id=request.agent_id,
        max_results=request.max_results,
    )
    
    return [
        SkillMatchResponse(
            skill=SkillResponse(
                id=m.skill.id,
                name=m.skill.name,
                description=m.skill.description,
                category=m.skill.category,
                trigger_keywords=m.skill.trigger_keywords,
                implementation=m.skill.implementation,
                success_rate=m.skill.success_rate,
                usage_count=m.skill.usage_count,
            ),
            score=m.score,
            match_type=m.match_type,
            confidence=m.confidence,
        )
        for m in matches
    ]


@router.post("/learn", response_model=SkillResponse)
async def learn_from_task(
    request: LearnRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    从任务执行中学习
    
    提交任务执行记录，系统将：
    1. 记录任务轨迹
    2. 提取经验
    3. 生成技能
    
    返回生成的技能
    """
    if request.success not in ["success", "partial", "failure"]:
        raise HTTPException(
            status_code=400,
            detail="success 必须是 success/partial/failure 之一"
        )
    
    service = await get_learning_service(db)
    
    skill = await service.learn_from_task(
        agent_id=request.agent_id,
        task_description=request.task_description,
        decisions=request.decisions,
        outcomes=request.outcomes,
        success=request.success,
        session_id=request.session_id,
        task_id=request.task_id,
    )
    
    if not skill:
        raise HTTPException(
            status_code=422,
            detail="无法从任务中提取有效经验"
        )
    
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        category=skill.category,
        trigger_keywords=skill.trigger_keywords,
        implementation=skill.implementation,
        success_rate=skill.success_rate,
        usage_count=skill.usage_count,
    )


@router.get("/agent/{agent_id}/stats", response_model=LearningStatsResponse)
async def get_agent_learning_stats(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取 Agent 的学习统计"""
    service = await get_learning_service(db)
    stats = await service.get_agent_learning_stats(agent_id)
    return LearningStatsResponse(**stats)


@router.post("/{skill_id}/feedback")
async def update_skill_feedback(
    skill_id: str,
    success: bool,
    db: AsyncSession = Depends(get_db),
):
    """
    更新技能反馈
    
    根据技能在实际任务中的表现更新评分
    - success=True: 提高成功率
    - success=False: 降低成功率
    """
    service = await get_learning_service(db)
    
    skill = await service.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    await service.update_skill_feedback(skill_id, success)
    
    updated_skill = await service.get_skill_by_id(skill_id)
    
    return {
        "message": "反馈已更新",
        "skill_id": skill_id,
        "new_success_rate": updated_skill.success_rate if updated_skill else 0,
    }
