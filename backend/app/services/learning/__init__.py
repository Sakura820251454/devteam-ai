"""
Phase 4.3 自我学习模块

实现完整的自我学习闭环：
- 轨迹记录 (TrajectoryRecorder)
- 经验提取 (ExperienceExtractor)
- 技能管理 (SkillManager)
- 技能匹配 (SkillMatcher)
- 智能学习服务 (IntelligentLearningService)
"""

from app.services.learning.trajectory import TrajectoryRecorder
from app.services.learning.extractor import ExperienceExtractor
from app.services.learning.skill_manager import SkillManager, Skill
from app.services.learning.matcher import SkillMatcher, SkillMatch
from app.services.learning.intelligent_learning import IntelligentLearningService, get_learning_service

__all__ = [
    "TrajectoryRecorder",
    "ExperienceExtractor",
    "SkillManager",
    "Skill",
    "SkillMatcher",
    "SkillMatch",
    "IntelligentLearningService",
    "get_learning_service",
]
