"""
经验提取引擎 - Phase 4.3

从轨迹中提取可复用的经验和模式
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

from app.services.learning.trajectory import Trajectory, Decision


@dataclass
class ExtractedExperience:
    """提取的经验"""
    id: str
    title: str
    description: str
    category: str
    steps: List[str]
    key_decisions: List[str]
    success_factors: List[str]
    pitfalls: List[str]
    keywords: List[str]
    source_trajectory_id: str


class ExperienceExtractor:
    """经验提取引擎"""
    
    def __init__(self):
        self.category_patterns = {
            "coding": ["代码", "编程", "实现", "函数", "类", "API", "调试"],
            "testing": ["测试", "单元测试", "集成测试", "覆盖率", "bug"],
            "planning": ["规划", "任务", "分解", "排期", "里程碑"],
            "communication": ["沟通", "协调", "团队", "会议", "反馈"],
            "debugging": ["调试", "错误", "排查", "定位", "修复"],
            "optimization": ["优化", "性能", "效率", "速度", "内存"],
        }
    
    def extract_from_trajectory(
        self,
        trajectory: Trajectory,
    ) -> Optional[ExtractedExperience]:
        """
        从单个轨迹提取经验
        
        Args:
            trajectory: 任务执行轨迹
            
        Returns:
            ExtractedExperience if successful, None otherwise
        """
        if not trajectory.decisions:
            return None
        
        # 确定经验分类
        category = self._determine_category(trajectory)
        
        # 提取关键步骤
        steps = self._extract_steps(trajectory)
        
        # 提取关键决策
        key_decisions = self._extract_key_decisions(trajectory)
        
        # 分析成功/失败因素
        success_factors, pitfalls = self._analyze_factors(trajectory)
        
        # 提取关键词
        keywords = self._extract_keywords(trajectory)
        
        # 生成标题和描述
        title = self._generate_title(trajectory)
        description = self._generate_description(trajectory)
        
        return ExtractedExperience(
            id=f"exp_{trajectory.id}",
            title=title,
            description=description,
            category=category,
            steps=steps,
            key_decisions=key_decisions,
            success_factors=success_factors,
            pitfalls=pitfalls,
            keywords=keywords,
            source_trajectory_id=trajectory.id,
        )
    
    def extract_multiple_trajectories(
        self,
        trajectories: List[Trajectory],
    ) -> List[ExtractedExperience]:
        """从多个轨迹批量提取经验"""
        experiences = []
        
        for trajectory in trajectories:
            exp = self.extract_from_trajectory(trajectory)
            if exp:
                experiences.append(exp)
        
        return experiences
    
    def _determine_category(self, trajectory: Trajectory) -> str:
        """确定经验分类"""
        content_lower = trajectory.content.lower()
        
        for category, keywords in self.category_patterns.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return category
        
        return "general"
    
    def _extract_steps(self, trajectory: Trajectory) -> List[str]:
        """从决策中提取执行步骤"""
        steps = []
        
        for decision in sorted(trajectory.decisions, key=lambda d: d.step):
            if decision.action and len(decision.action.strip()) > 0:
                steps.append(decision.action)
        
        return steps
    
    def _extract_key_decisions(self, trajectory: Trajectory) -> List[str]:
        """提取关键决策"""
        key_decisions = []
        
        for decision in trajectory.decisions:
            if decision.reasoning and len(decision.reasoning.strip()) > 0:
                key_decisions.append(decision.reasoning)
        
        return key_decisions
    
    def _analyze_factors(
        self,
        trajectory: Trajectory,
    ) -> tuple[List[str], List[str]]:
        """分析成功因素和陷阱"""
        success_factors = []
        pitfalls = []
        
        # 从 outcomes 分析
        for key, value in trajectory.outcomes.items():
            key_lower = key.lower()
            if "success" in key_lower or "win" in key_lower or "good" in key_lower:
                success_factors.append(f"{key}: {value}")
            elif "fail" in key_lower or "error" in key_lower or "problem" in key_lower:
                pitfalls.append(f"{key}: {value}")
        
        # 根据 success 标记
        if trajectory.success == "success":
            success_factors.append("任务完成方式有效")
        elif trajectory.success == "failure":
            pitfalls.append("执行流程需要改进")
        elif trajectory.success == "partial":
            success_factors.append("部分目标达成")
            pitfalls.append("部分目标未达成")
        
        return success_factors, pitfalls
    
    def _extract_keywords(self, trajectory: Trajectory) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # 从分类模式提取
        content = trajectory.content.lower()
        for category, pattern_keywords in self.category_patterns.items():
            for kw in pattern_keywords:
                if kw in content:
                    keywords.append(kw)
        
        # 从决策中提取
        for decision in trajectory.decisions:
            action = decision.action.lower()
            for category, pattern_keywords in self.category_patterns.items():
                for kw in pattern_keywords:
                    if kw in action and kw not in keywords:
                        keywords.append(kw)
        
        return keywords
    
    def _generate_title(self, trajectory: Trajectory) -> str:
        """生成经验标题"""
        # 使用任务描述的前 50 字符
        base_title = trajectory.content[:50]
        if len(trajectory.content) > 50:
            base_title += "..."
        
        # 添加成功/失败标记
        if trajectory.success == "success":
            return f"✅ {base_title}"
        elif trajectory.success == "failure":
            return f"❌ {base_title}"
        else:
            return f"📝 {base_title}"
    
    def _generate_description(self, trajectory: Trajectory) -> str:
        """生成经验描述"""
        parts = [f"任务: {trajectory.content}"]
        
        if trajectory.decisions:
            parts.append(f"\n关键步骤: {len(trajectory.decisions)} 步")
        
        if trajectory.success:
            success_map = {
                "success": "成功",
                "partial": "部分成功",
                "failure": "失败",
            }
            parts.append(f"\n结果: {success_map.get(trajectory.success, trajectory.success)}")
        
        if trajectory.outcomes:
            parts.append("\n关键产出:")
            for key, value in list(trajectory.outcomes.items())[:3]:
                parts.append(f"  - {key}: {value}")
        
        return "\n".join(parts)
    
    def aggregate_experiences(
        self,
        experiences: List[ExtractedExperience],
    ) -> Dict[str, List[ExtractedExperience]]:
        """按分类聚合经验"""
        aggregated = defaultdict(list)
        
        for exp in experiences:
            aggregated[exp.category].append(exp)
        
        return dict(aggregated)
