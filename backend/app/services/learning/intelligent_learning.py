"""
智能学习服务 - Phase 4 优化

自动化的学习闭环：
- 自动轨迹记录
- 自动经验提取
- 自动技能生成
- 智能技能推荐
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import asyncio

from app.services.learning.trajectory import TrajectoryRecorder, Trajectory
from app.services.learning.extractor import ExperienceExtractor
from app.services.learning.skill_manager import SkillManager, Skill
from app.services.learning.matcher import SkillMatcher, SkillMatch


class IntelligentLearningService:
    """
    智能学习服务
    
    提供自动化的学习闭环，支持：
    - 自动轨迹记录装饰器
    - 任务完成后自动经验提取
    - 自动技能生成
    - 智能技能推荐
    """
    
    def __init__(
        self,
        db=None,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ):
        self.db = db
        self.recorder = TrajectoryRecorder(db)
        self.extractor = ExperienceExtractor()
        self.skill_manager = SkillManager(db)
        self.matcher = SkillMatcher(
            self.skill_manager,
            use_vector_search=True,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
        )
        
        self._active_trajectories: Dict[str, Dict[str, Any]] = {}
    
    def task_tracker(
        self,
        agent_id: str,
        task_description: str,
        session_id: Optional[str] = None,
    ) -> Callable:
        """
        任务跟踪装饰器
        
        用法:
        ```python
        learning_service = IntelligentLearningService(db)
        
        @learning_service.task_tracker("agent_001", "开发用户登录功能")
        async def execute_task(task):
            # 任务执行逻辑
            pass
        ```
        """
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                trajectory_id = self.start_tracking(
                    agent_id=agent_id,
                    task_description=task_description,
                    session_id=session_id,
                )
                
                try:
                    result = await func(*args, **kwargs)
                    
                    success = result.get("success", False) if isinstance(result, dict) else True
                    self.end_tracking(
                        trajectory_id=trajectory_id,
                        success="success" if success else "failure",
                        outcomes=result if isinstance(result, dict) else {"result": str(result)[:500]},
                    )
                    
                    return result
                    
                except Exception as e:
                    self.end_tracking(
                        trajectory_id=trajectory_id,
                        success="failure",
                        outcomes={"error": str(e)[:500]},
                    )
                    raise
            
            return wrapper
        return decorator
    
    async def record_decision(
        self,
        trajectory_id: str,
        step: int,
        action: str,
        reasoning: str,
    ) -> bool:
        """记录决策步骤"""
        return self.recorder.record_decision(
            trajectory_id=trajectory_id,
            step=step,
            action=action,
            reasoning=reasoning,
        )
    
    def start_tracking(
        self,
        agent_id: str,
        task_description: str,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """开始任务跟踪"""
        trajectory_id = self.recorder.start_trajectory(
            agent_id=agent_id,
            task_description=task_description,
            session_id=session_id,
            task_id=task_id,
        )
        
        self._active_trajectories[trajectory_id] = {
            "agent_id": agent_id,
            "session_id": session_id,
            "task_id": task_id,
            "step_counter": 0,
        }
        
        return trajectory_id
    
    def end_tracking(
        self,
        trajectory_id: str,
        success: str = "success",
        outcomes: Optional[Dict[str, Any]] = None,
    ) -> Optional[Trajectory]:
        """结束任务跟踪"""
        if trajectory_id in self._active_trajectories:
            del self._active_trajectories[trajectory_id]
        
        return self.recorder.end_trajectory(
            trajectory_id=trajectory_id,
            success=success,
        )
    
    async def learn_from_task(
        self,
        agent_id: str,
        task_description: str,
        decisions: List[Dict[str, str]],
        outcomes: Dict[str, Any],
        success: str = "success",
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Optional[Skill]:
        """
        从任务执行中学习
        
        完整流程：
        1. 记录轨迹
        2. 提取经验
        3. 生成技能
        4. 保存技能
        
        Args:
            agent_id: Agent ID
            task_description: 任务描述
            decisions: 决策列表 [{"step": 1, "action": "...", "reasoning": "..."}]
            outcomes: 执行结果
            success: 成功状态
            session_id: 会话 ID
            task_id: 任务 ID
            
        Returns:
            生成的技能，如果没有有效经验则返回 None
        """
        trajectory_id = self.start_tracking(
            agent_id=agent_id,
            task_description=task_description,
            session_id=session_id,
            task_id=task_id,
        )
        
        for decision in decisions:
            self.recorder.record_decision(
                trajectory_id=trajectory_id,
                step=decision.get("step", 0),
                action=decision.get("action", ""),
                reasoning=decision.get("reasoning", ""),
            )
        
        for key, value in outcomes.items():
            self.recorder.record_outcome(trajectory_id, key, value)
        
        trajectory = self.end_tracking(trajectory_id, success)
        
        if not trajectory:
            return None
        
        experience = self.extractor.extract_from_trajectory(trajectory)
        if not experience:
            return None
        
        skill = self.skill_manager.create_skill_from_experience(experience)
        
        if self.db:
            await self.skill_manager.save_skill(skill)
            await self.matcher.add_skill_to_vector_index(skill)
            await self.skill_manager.associate_skill_with_agent(
                agent_id=agent_id,
                skill_id=skill.id,
                confidence=1.0 if success == "success" else 0.5,
            )
        
        return skill
    
    async def recommend_skills(
        self,
        task_description: str,
        agent_id: Optional[str] = None,
        max_results: int = 5,
    ) -> List[SkillMatch]:
        """
        推荐相关技能
        
        Args:
            task_description: 当前任务描述
            agent_id: Agent ID (优先匹配该 Agent 的技能)
            max_results: 最大返回数量
            
        Returns:
            技能匹配列表，按相关度排序
        """
        return await self.matcher.match_skills(
            task_description=task_description,
            agent_id=agent_id,
            max_results=max_results,
        )
    
    async def get_agent_learning_stats(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """获取 Agent 的学习统计"""
        if not self.db:
            return {
                "total_trajectories": 0,
                "total_skills": 0,
                "skills_by_category": {},
            }
        
        trajectories = await self.recorder.get_agent_trajectories(agent_id)
        skills_with_confidence = await self.skill_manager.get_agent_skills(agent_id)
        
        category_stats = {}
        for skill, confidence in skills_with_confidence:
            if skill.category not in category_stats:
                category_stats[skill.category] = {"count": 0, "total_confidence": 0}
            category_stats[skill.category]["count"] += 1
            category_stats[skill.category]["total_confidence"] += confidence
        
        for category in category_stats:
            count = category_stats[category]["count"]
            total = category_stats[category]["total_confidence"]
            category_stats[category]["avg_confidence"] = total / count if count > 0 else 0
        
        successful_trajectories = [t for t in trajectories if t.success == "success"]
        
        return {
            "total_trajectories": len(trajectories),
            "successful_trajectories": len(successful_trajectories),
            "success_rate": len(successful_trajectories) / len(trajectories) if trajectories else 0,
            "total_skills": len(skills_with_confidence),
            "skills_by_category": category_stats,
        }
    
    async def get_skill_by_id(
        self,
        skill_id: str,
    ) -> Optional[Skill]:
        """获取单个技能"""
        return await self.skill_manager.get_skill(skill_id)
    
    async def get_skills_by_category(
        self,
        category: str,
        limit: int = 50,
    ) -> List[Skill]:
        """按分类获取技能"""
        return await self.skill_manager.get_skills_by_category(category, limit)
    
    async def update_skill_feedback(
        self,
        skill_id: str,
        success: bool,
    ) -> bool:
        """更新技能反馈"""
        return await self.skill_manager.update_skill_success_rate(skill_id, success)


learning_service: Optional[IntelligentLearningService] = None


async def get_learning_service(db=None) -> IntelligentLearningService:
    """获取学习服务单例"""
    global learning_service
    if learning_service is None:
        learning_service = IntelligentLearningService(db=db)
    else:
        learning_service.db = db
    return learning_service
