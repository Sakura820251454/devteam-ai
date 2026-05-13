"""
技能匹配器 - Phase 4.3

根据任务描述匹配相关技能
支持关键词匹配和向量相似度匹配
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.services.learning.skill_manager import SkillManager, Skill
from app.services.memory.vector_store import get_vector_store


@dataclass
class SkillMatch:
    """技能匹配结果"""
    skill: Skill
    score: float
    match_type: str  # "keyword", "vector", "hybrid"
    confidence: float


class SkillMatcher:
    """技能匹配器"""
    
    def __init__(
        self,
        skill_manager: SkillManager,
        use_vector_search: bool = True,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ):
        self.skill_manager = skill_manager
        self.use_vector_search = use_vector_search
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
    
    async def match_skills(
        self,
        task_description: str,
        agent_id: Optional[str] = None,
        max_results: int = 5,
        min_score: float = 0.0,
    ) -> List[SkillMatch]:
        """
        匹配相关技能
        
        Args:
            task_description: 任务描述
            agent_id: 可选，优先匹配 Agent 的技能
            max_results: 最大返回数量
            min_score: 最低匹配分数
            
        Returns:
            排序后的技能匹配列表
        """
        # 获取候选技能池
        if agent_id:
            agent_skills = await self.skill_manager.get_agent_skills(agent_id)
            skills = [skill for skill, _ in agent_skills]
        else:
            skills = await self.skill_manager.get_all_skills()
        
        if not skills:
            return []
        
        # 计算匹配分数
        matches = []
        for skill in skills:
            score, match_type = await self._calculate_match_score(
                skill,
                task_description,
            )
            
            if score >= min_score:
                matches.append(SkillMatch(
                    skill=skill,
                    score=score,
                    match_type=match_type,
                    confidence=skill.success_rate,
                ))
        
        # 排序
        matches.sort(
            key=lambda m: (m.score * self.vector_weight + m.confidence * self.keyword_weight),
            reverse=True,
        )
        
        return matches[:max_results]
    
    async def _calculate_match_score(
        self,
        skill: Skill,
        task_description: str,
    ) -> Tuple[float, str]:
        """
        计算技能与任务的匹配分数
        
        Returns:
            (score, match_type)
        """
        # 关键词匹配
        keyword_score = self._keyword_match_score(skill, task_description)
        
        # 向量匹配
        vector_score = 0.0
        if self.use_vector_search:
            vector_score = await self._vector_match_score(skill, task_description)
        
        # 综合评分
        if keyword_score > 0 and vector_score > 0:
            hybrid_score = (
                keyword_score * self.keyword_weight +
                vector_score * self.vector_weight
            )
            return hybrid_score, "hybrid"
        elif keyword_score > 0:
            return keyword_score, "keyword"
        elif vector_score > 0:
            return vector_score, "vector"
        else:
            return 0.0, "none"
    
    def _keyword_match_score(
        self,
        skill: Skill,
        task_description: str,
    ) -> float:
        """关键词匹配分数"""
        task_lower = task_description.lower()
        
        # 统计匹配的触发关键词
        match_count = 0
        for keyword in skill.trigger_keywords:
            if keyword.lower() in task_lower:
                match_count += 1
        
        if not skill.trigger_keywords:
            return 0.0
        
        # 归一化到 0-1
        keyword_score = min(match_count / len(skill.trigger_keywords), 1.0)
        
        # 额外加分：技能名称包含关键词
        if skill.name.lower() in task_lower:
            keyword_score += 0.2
        
        return min(keyword_score, 1.0)
    
    async def _vector_match_score(
        self,
        skill: Skill,
        task_description: str,
    ) -> float:
        """向量匹配分数"""
        try:
            vector_store = await get_vector_store()
            
            # 构造搜索查询：技能名称 + 描述
            query = f"{skill.name} {skill.description}"
            
            # 在向量库中搜索
            results = await vector_store.search(
                query=task_description,
                k=10,
            )
            
            # 检查是否存在该技能的向量
            skill_doc = await vector_store.get_document(skill.id)
            
            if skill_doc and skill_doc.embedding is not None:
                # 使用技能向量直接匹配（简化）
                task_embedding = vector_store._get_embedding(task_description)
                skill_embedding = skill_doc.embedding
                
                # 余弦相似度计算
                import numpy as np
                similarity = np.dot(task_embedding, skill_embedding) / (
                    np.linalg.norm(task_embedding) * np.linalg.norm(skill_embedding)
                )
                
                return float(similarity) * 0.5 + 0.5  # 归一化到 0-1
            
            return 0.0
            
        except Exception:
            return 0.0
    
    async def add_skill_to_vector_index(
        self,
        skill: Skill,
    ) -> bool:
        """将技能添加到向量索引"""
        try:
            vector_store = await get_vector_store()
            
            content = f"{skill.name}\n{skill.description}"
            metadata = {
                "skill_id": skill.id,
                "category": skill.category,
                "trigger_keywords": skill.trigger_keywords,
            }
            
            await vector_store.add_document(
                doc_id=skill.id,
                content=content,
                metadata=metadata,
            )
            
            return True
        except Exception:
            return False
    
    async def index_all_skills(self) -> int:
        """索引所有技能"""
        skills = await self.skill_manager.get_all_skills()
        count = 0
        
        for skill in skills:
            if await self.add_skill_to_vector_index(skill):
                count += 1
        
        return count
    
    def recommend_best_skill(
        self,
        matches: List[SkillMatch],
    ) -> Optional[SkillMatch]:
        """推荐最佳匹配技能"""
        if not matches:
            return None
        
        # 综合考虑匹配分数和成功率
        best = max(
            matches,
            key=lambda m: (
                m.score * 0.6 +
                m.confidence * 0.3 +
                (m.skill.usage_count / 100) * 0.1
            ),
        )
        
        return best
