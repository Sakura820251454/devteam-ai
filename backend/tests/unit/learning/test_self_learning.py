"""
Phase 4.3 自我学习测试

测试完整的自我学习闭环
"""

import pytest
import pytest_asyncio
from datetime import datetime

from app.services.learning.trajectory import (
    TrajectoryRecorder,
    Trajectory,
    Decision,
)
from app.services.learning.extractor import (
    ExperienceExtractor,
    ExtractedExperience,
)
from app.services.learning.skill_manager import (
    SkillManager,
    Skill,
)
from app.services.learning.matcher import (
    SkillMatcher,
    SkillMatch,
)


class TestTrajectoryRecorder:
    """轨迹记录器测试"""
    
    def test_start_trajectory(self):
        """测试开始轨迹"""
        recorder = TrajectoryRecorder()
        traj_id = recorder.start_trajectory(
            agent_id="test_agent",
            task_description="编写 Python 单元测试",
        )
        
        assert traj_id.startswith("traj_test_agent_")
        assert traj_id in recorder.current_trajectories
    
    def test_record_decision(self):
        """测试记录决策"""
        recorder = TrajectoryRecorder()
        traj_id = recorder.start_trajectory(
            agent_id="test_agent",
            task_description="编写 Python 单元测试",
        )
        
        success = recorder.record_decision(
            trajectory_id=traj_id,
            step=1,
            action="分析需求",
            reasoning="理解测试目标和范围",
        )
        
        assert success
        trajectory = recorder.current_trajectories[traj_id]
        assert len(trajectory.decisions) == 1
        assert trajectory.decisions[0].action == "分析需求"
    
    def test_record_outcome(self):
        """测试记录结果"""
        recorder = TrajectoryRecorder()
        traj_id = recorder.start_trajectory(
            agent_id="test_agent",
            task_description="编写 Python 单元测试",
        )
        
        success = recorder.record_outcome(
            trajectory_id=traj_id,
            key="tests_written",
            value=5,
        )
        
        assert success
        trajectory = recorder.current_trajectories[traj_id]
        assert trajectory.outcomes["tests_written"] == 5
    
    def test_end_trajectory(self):
        """测试结束轨迹"""
        recorder = TrajectoryRecorder()
        traj_id = recorder.start_trajectory(
            agent_id="test_agent",
            task_description="编写 Python 单元测试",
        )
        
        trajectory = recorder.end_trajectory(
            trajectory_id=traj_id,
            success="success",
        )
        
        assert trajectory is not None
        assert trajectory.success == "success"
        assert traj_id not in recorder.current_trajectories


class TestExperienceExtractor:
    """经验提取器测试"""
    
    @pytest.fixture
    def sample_trajectory(self):
        """示例轨迹"""
        return Trajectory(
            id="traj_123",
            agent_id="test_agent",
            session_id="session_456",
            task_id=None,
            content="编写并运行 Python 单元测试",
            decisions=[
                Decision(
                    step=1,
                    action="分析需求",
                    reasoning="理解测试目标：验证用户登录功能",
                ),
                Decision(
                    step=2,
                    action="编写测试用例",
                    reasoning="覆盖正常登录和错误场景",
                ),
                Decision(
                    step=3,
                    action="运行测试",
                    reasoning="执行所有测试用例，检查覆盖率",
                ),
            ],
            outcomes={
                "tests_passed": 8,
                "tests_failed": 0,
                "coverage": "85%",
            },
            success="success",
        )
    
    def test_extract_from_trajectory(self, sample_trajectory):
        """测试从轨迹提取经验"""
        extractor = ExperienceExtractor()
        experience = extractor.extract_from_trajectory(sample_trajectory)
        
        assert experience is not None
        assert experience.title.startswith("✅")
        assert experience.category == "testing"
        assert len(experience.steps) == 3
        assert len(experience.keywords) > 0
    
    def test_aggregate_experiences(self, sample_trajectory):
        """测试经验聚合"""
        extractor = ExperienceExtractor()
        
        experiences = [
            extractor.extract_from_trajectory(sample_trajectory),
            extractor.extract_from_trajectory(sample_trajectory),
        ]
        
        aggregated = extractor.aggregate_experiences(experiences)
        assert "testing" in aggregated
        assert len(aggregated["testing"]) == 2


class TestSkillManager:
    """技能管理器测试"""
    
    @pytest.fixture
    def sample_trajectory(self):
        """示例轨迹"""
        return Trajectory(
            id="traj_123",
            agent_id="test_agent",
            session_id="session_456",
            task_id=None,
            content="编写并运行 Python 单元测试",
            decisions=[
                Decision(
                    step=1,
                    action="分析需求",
                    reasoning="理解测试目标：验证用户登录功能",
                ),
                Decision(
                    step=2,
                    action="编写测试用例",
                    reasoning="覆盖正常登录和错误场景",
                ),
                Decision(
                    step=3,
                    action="运行测试",
                    reasoning="执行所有测试用例，检查覆盖率",
                ),
            ],
            outcomes={
                "tests_passed": 8,
                "tests_failed": 0,
                "coverage": "85%",
            },
            success="success",
        )
    
    @pytest.fixture
    def sample_experience(self, sample_trajectory):
        """示例经验"""
        extractor = ExperienceExtractor()
        return extractor.extract_from_trajectory(sample_trajectory)
    
    def test_create_skill_from_experience(self, sample_experience):
        """测试从经验创建技能"""
        manager = SkillManager()
        skill = manager.create_skill_from_experience(sample_experience)
        
        assert skill is not None
        assert skill.id.startswith("skill_")
        assert skill.category == sample_experience.category
        assert len(skill.trigger_keywords) > 0
        assert "steps" in skill.implementation


class TestSkillMatcher:
    """技能匹配器测试"""
    
    @pytest.fixture
    def sample_skills(self):
        """示例技能"""
        return [
            Skill(
                id="skill_1",
                name="Python 单元测试",
                description="编写和运行 Python 单元测试",
                category="testing",
                trigger_keywords=["测试", "单元测试", "Python", "coverage"],
            ),
            Skill(
                id="skill_2",
                name="API 开发",
                description="使用 FastAPI 开发 REST API",
                category="coding",
                trigger_keywords=["API", "FastAPI", "REST", "后端"],
            ),
        ]
    
    def test_keyword_match(self, sample_skills):
        """测试关键词匹配"""
        manager = SkillManager()
        matcher = SkillMatcher(manager, use_vector_search=False)
        
        skill = sample_skills[0]
        score = matcher._keyword_match_score(
            skill,
            "编写 Python 单元测试来验证用户登录",
        )
        
        assert score > 0
    
    def test_recommend_best_skill(self, sample_skills):
        """测试推荐最佳技能"""
        manager = SkillManager()
        matcher = SkillMatcher(manager, use_vector_search=False)
        
        matches = [
            SkillMatch(
                skill=sample_skills[0],
                score=0.8,
                match_type="keyword",
                confidence=0.9,
            ),
            SkillMatch(
                skill=sample_skills[1],
                score=0.5,
                match_type="keyword",
                confidence=0.7,
            ),
        ]
        
        best = matcher.recommend_best_skill(matches)
        assert best is not None
        assert best.skill.id == "skill_1"


class TestEndToEndLearning:
    """端到端学习流程测试"""
    
    def test_complete_learning_cycle(self):
        """测试完整学习闭环"""
        # 1. 记录轨迹
        recorder = TrajectoryRecorder()
        traj_id = recorder.start_trajectory(
            agent_id="dev_agent",
            task_description="优化数据库查询性能",
        )
        
        recorder.record_decision(traj_id, 1, "分析慢查询", "识别性能瓶颈")
        recorder.record_decision(traj_id, 2, "添加索引", "优化 WHERE 条件字段")
        recorder.record_decision(traj_id, 3, "验证优化", "执行 EXPLAIN 检查")
        recorder.record_outcome(traj_id, "speed_improvement", "10x 提速")
        
        trajectory = recorder.end_trajectory(traj_id, success="success")
        
        # 2. 提取经验
        extractor = ExperienceExtractor()
        experience = extractor.extract_from_trajectory(trajectory)
        
        assert experience is not None
        assert "优化" in experience.keywords
        
        # 3. 创建技能
        manager = SkillManager()
        skill = manager.create_skill_from_experience(experience)
        
        assert skill is not None
        assert skill.category == "optimization"
        
        # 4. 匹配技能
        matcher = SkillMatcher(manager, use_vector_search=False)
        
        # 模拟技能已保存到管理器
        matcher.skill_manager._test_skills = [skill]
        
        # 直接测试关键词匹配
        score = matcher._keyword_match_score(skill, "如何优化数据库查询？")
        assert score > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
