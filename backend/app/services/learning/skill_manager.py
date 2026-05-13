"""
技能管理器 - Phase 4.3

管理技能库，包括：
- 创建和更新技能
- 技能持久化
- 技能评分和置信度
- Agent-技能关联
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.models.memory_db import SkillModel, AgentSkillModel
from app.services.learning.extractor import ExtractedExperience


@dataclass
class Skill:
    """技能"""
    id: str
    name: str
    description: str
    category: str
    trigger_keywords: List[str] = field(default_factory=list)
    implementation: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.0
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class SkillManager:
    """技能管理器"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
    
    def create_skill_from_experience(
        self,
        experience: ExtractedExperience,
    ) -> Skill:
        """
        从经验创建技能
        
        Args:
            experience: 提取的经验
            
        Returns:
            Skill
        """
        skill_id = f"skill_{datetime.now().timestamp()}"
        
        implementation = {
            "steps": experience.steps,
            "key_decisions": experience.key_decisions,
            "success_factors": experience.success_factors,
            "pitfalls": experience.pitfalls,
            "source_experience_id": experience.id,
        }
        
        return Skill(
            id=skill_id,
            name=experience.title,
            description=experience.description,
            category=experience.category,
            trigger_keywords=experience.keywords,
            implementation=implementation,
            success_rate=1.0 if experience.keywords else 0.5,  # 初始评分
        )
    
    async def save_skill(
        self,
        skill: Skill,
    ) -> bool:
        """保存技能到数据库"""
        if not self.db:
            return False
        
        model = SkillModel(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            category=skill.category,
            trigger_keywords=skill.trigger_keywords,
            implementation=skill.implementation,
            success_rate=skill.success_rate,
            usage_count=skill.usage_count,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
        )
        
        self.db.add(model)
        await self.db.commit()
        return True
    
    async def get_skill(
        self,
        skill_id: str,
    ) -> Optional[Skill]:
        """获取单个技能"""
        if not self.db:
            return None
        
        result = await self.db.execute(
            select(SkillModel).where(SkillModel.id == skill_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return Skill(
            id=model.id,
            name=model.name,
            description=model.description,
            category=model.category,
            trigger_keywords=model.trigger_keywords,
            implementation=model.implementation,
            success_rate=model.success_rate,
            usage_count=model.usage_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def get_skills_by_category(
        self,
        category: str,
        limit: int = 50,
    ) -> List[Skill]:
        """按分类获取技能"""
        if not self.db:
            return []
        
        result = await self.db.execute(
            select(SkillModel)
            .where(SkillModel.category == category)
            .order_by(SkillModel.success_rate.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        
        return [
            Skill(
                id=m.id,
                name=m.name,
                description=m.description,
                category=m.category,
                trigger_keywords=m.trigger_keywords,
                implementation=m.implementation,
                success_rate=m.success_rate,
                usage_count=m.usage_count,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in models
        ]
    
    async def get_all_skills(
        self,
        limit: int = 100,
    ) -> List[Skill]:
        """获取所有技能"""
        if not self.db:
            return []
        
        result = await self.db.execute(
            select(SkillModel)
            .order_by(SkillModel.usage_count.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        
        return [
            Skill(
                id=m.id,
                name=m.name,
                description=m.description,
                category=m.category,
                trigger_keywords=m.trigger_keywords,
                implementation=m.implementation,
                success_rate=m.success_rate,
                usage_count=m.usage_count,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in models
        ]
    
    async def update_skill_success_rate(
        self,
        skill_id: str,
        success: bool,
    ) -> bool:
        """更新技能成功率"""
        if not self.db:
            return False
        
        skill = await self.get_skill(skill_id)
        if not skill:
            return False
        
        # 简单的贝叶斯更新
        total = skill.usage_count + 1
        success_count = skill.success_rate * skill.usage_count + (1 if success else 0)
        new_rate = success_count / total
        
        await self.db.execute(
            update(SkillModel)
            .where(SkillModel.id == skill_id)
            .values(
                success_rate=new_rate,
                usage_count=skill.usage_count + 1,
                updated_at=datetime.now(),
            )
        )
        await self.db.commit()
        return True
    
    async def associate_skill_with_agent(
        self,
        agent_id: str,
        skill_id: str,
        confidence: float = 1.0,
    ) -> bool:
        """将技能关联到 Agent"""
        if not self.db:
            return False
        
        existing = await self.db.execute(
            select(AgentSkillModel).where(
                AgentSkillModel.agent_id == agent_id,
                AgentSkillModel.skill_id == skill_id,
            )
        )
        
        if existing.scalar_one_or_none():
            await self.db.execute(
                update(AgentSkillModel)
                .where(
                    AgentSkillModel.agent_id == agent_id,
                    AgentSkillModel.skill_id == skill_id,
                )
                .values(
                    confidence=confidence,
                )
            )
        else:
            association = AgentSkillModel(
                agent_id=agent_id,
                skill_id=skill_id,
                confidence=confidence,
            )
            self.db.add(association)
        
        await self.db.commit()
        return True
    
    async def get_agent_skills(
        self,
        agent_id: str,
        min_confidence: float = 0.0,
    ) -> List[tuple[Skill, float]]:
        """获取 Agent 的技能"""
        if not self.db:
            return []
        
        result = await self.db.execute(
            select(AgentSkillModel, SkillModel)
            .join(SkillModel, AgentSkillModel.skill_id == SkillModel.id)
            .where(
                AgentSkillModel.agent_id == agent_id,
                AgentSkillModel.confidence >= min_confidence,
            )
            .order_by(AgentSkillModel.confidence.desc())
        )
        
        results = result.all()
        
        return [
            (
                Skill(
                    id=skill.id,
                    name=skill.name,
                    description=skill.description,
                    category=skill.category,
                    trigger_keywords=skill.trigger_keywords,
                    implementation=skill.implementation,
                    success_rate=skill.success_rate,
                    usage_count=skill.usage_count,
                    created_at=skill.created_at,
                    updated_at=skill.updated_at,
                ),
                association.confidence,
            )
            for association, skill in results
        ]
    
    async def delete_skill(
        self,
        skill_id: str,
    ) -> bool:
        """删除技能"""
        if not self.db:
            return False
        
        await self.db.execute(
            delete(AgentSkillModel).where(AgentSkillModel.skill_id == skill_id)
        )
        await self.db.execute(
            delete(SkillModel).where(SkillModel.id == skill_id)
        )
        await self.db.commit()
        return True
