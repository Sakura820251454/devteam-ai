"""
记忆遗忘机制测试

测试记忆遗忘功能
"""

import pytest
from datetime import datetime, timedelta

from app.services.memory.memory_forget import (
    MemoryForgetService,
    CapacityManager,
    ForgetPolicy,
    ForgetReason,
    ForgetCandidate,
)


class TestMemoryForgetService:
    """记忆遗忘服务测试"""
    
    def test_evaluate_forget_candidates_quality(self):
        """测试基于质量的遗忘评估"""
        service = MemoryForgetService(ForgetPolicy(min_quality_threshold=0.3))
        
        memories = [
            {
                "id": "low_quality",
                "level": "working",
                "relevance_score": 0.1,
                "usage_count": 0,
                "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=60)).isoformat(),
            },
            {
                "id": "high_quality",
                "level": "working",
                "relevance_score": 0.9,
                "usage_count": 10,
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            },
        ]
        
        candidates = service.evaluate_forget_candidates(memories, "test_agent")
        
        assert len(candidates) == 1
        assert candidates[0].memory_id == "low_quality"
    
    def test_evaluate_forget_candidates_time(self):
        """测试基于时间的遗忘"""
        service = MemoryForgetService(
            ForgetPolicy(
                max_age_days=30,
                min_quality_threshold=0.0  # 确保质量不会优先
            )
        )
        
        memories = [
            {
                "id": "old_memory",
                "level": "working",
                "relevance_score": 0.8,
                "usage_count": 5,
                "created_at": (datetime.now() - timedelta(days=400)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=400)).isoformat(),
            },
        ]
        
        candidates = service.evaluate_forget_candidates(memories, "test_agent")
        
        assert len(candidates) == 1
        assert candidates[0].reason == ForgetReason.TIME_EXPIRED
    
    def test_evaluate_forget_candidates_not_accessed(self):
        """测试长期未访问的遗忘"""
        service = MemoryForgetService(ForgetPolicy(not_accessed_days=30))
        
        memories = [
            {
                "id": "not_accessed",
                "level": "working",
                "relevance_score": 0.8,
                "usage_count": 5,
                "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=100)).isoformat(),
            },
        ]
        
        candidates = service.evaluate_forget_candidates(memories, "test_agent")
        
        assert len(candidates) == 1
        assert candidates[0].reason == ForgetReason.NOT_ACCESSED
    
    def test_preserve_important_memory(self):
        """测试重要记忆不被遗忘"""
        service = MemoryForgetService(
            ForgetPolicy(preserve_important=True, min_quality_threshold=0.5)
        )
        
        memories = [
            {
                "id": "important",
                "level": "working",
                "relevance_score": 0.1,
                "usage_count": 0,
                "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=60)).isoformat(),
                "metadata": {"important": True},
            },
        ]
        
        candidates = service.evaluate_forget_candidates(memories, "test_agent")
        
        assert len(candidates) == 0
    
    def test_preserve_recent_memory(self):
        """测试最近记忆不被遗忘"""
        service = MemoryForgetService(
            ForgetPolicy(preserve_recent=True, recent_days=7)
        )
        
        memories = [
            {
                "id": "recent",
                "level": "working",
                "relevance_score": 0.1,
                "usage_count": 0,
                "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=2)).isoformat(),
            },
        ]
        
        candidates = service.evaluate_forget_candidates(memories, "test_agent")
        
        assert len(candidates) == 0
    
    def test_priority_ordering(self):
        """测试遗忘优先级排序"""
        service = MemoryForgetService(
            ForgetPolicy(
                min_quality_threshold=0.0,  # 不基于质量
                not_accessed_days=30
            )
        )
        
        memories = [
            {
                "id": "not_accessed_1",
                "level": "working",
                "relevance_score": 0.8,
                "usage_count": 5,
                "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=100)).isoformat(),
            },
            {
                "id": "not_accessed_2",
                "level": "working",
                "relevance_score": 0.8,
                "usage_count": 5,
                "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=50)).isoformat(),
            },
        ]
        
        candidates = service.evaluate_forget_candidates(memories, "test_agent")
        
        assert len(candidates) == 2
        assert candidates[0].days_since_access >= candidates[1].days_since_access
    
    def test_get_forget_plan(self):
        """测试遗忘计划生成"""
        service = MemoryForgetService(
            ForgetPolicy(min_quality_threshold=0.3, not_accessed_days=30)
        )
        
        memories = [
            {
                "id": "to_forget_1",
                "level": "working",
                "relevance_score": 0.1,
                "usage_count": 0,
                "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=60)).isoformat(),
            },
            {
                "id": "to_forget_2",
                "level": "short_term",
                "relevance_score": 0.2,
                "usage_count": 1,
                "created_at": (datetime.now() - timedelta(days=100)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=100)).isoformat(),
            },
            {
                "id": "keep",
                "level": "working",
                "relevance_score": 0.8,
                "usage_count": 10,
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            },
        ]
        
        plan = service.get_forget_plan(memories, "test_agent")
        
        assert plan["total_memories"] == 3
        assert plan["candidate_count"] == 2
        assert plan["forget_count"] == 2


class TestCapacityManager:
    """容量管理器测试"""
    
    def test_check_capacity_normal(self):
        """测试正常容量状态"""
        manager = CapacityManager(max_per_level=100, max_total=500)
        
        memories = [
            {"id": "m1", "level": "working", "relevance_score": 0.5},
            {"id": "m2", "level": "short_term", "relevance_score": 0.5},
            {"id": "m3", "level": "long_term", "relevance_score": 0.5},
        ]
        
        status = manager.check_capacity(memories)
        
        assert status["total"] == 3
        assert not status["total_exceeded"]
        assert not any(status["level_exceeded"].values())
    
    def test_check_capacity_exceeded(self):
        """测试容量超限"""
        manager = CapacityManager(max_per_level=2, max_total=5)
        
        memories = [
            {"id": "m1", "level": "working", "relevance_score": 0.5},
            {"id": "m2", "level": "working", "relevance_score": 0.5},
            {"id": "m3", "level": "working", "relevance_score": 0.5},
            {"id": "m4", "level": "working", "relevance_score": 0.5},
            {"id": "m5", "level": "working", "relevance_score": 0.5},
        ]
        
        status = manager.check_capacity(memories)
        
        assert status["total"] == 5
        assert not status["total_exceeded"]
        assert status["level_exceeded"]["working"]
    
    def test_check_total_exceeded(self):
        """测试总容量超限"""
        manager = CapacityManager(max_per_level=100, max_total=3)
        
        memories = [
            {"id": "m1", "level": "working", "relevance_score": 0.5},
            {"id": "m2", "level": "working", "relevance_score": 0.5},
            {"id": "m3", "level": "working", "relevance_score": 0.5},
            {"id": "m4", "level": "working", "relevance_score": 0.5},
        ]
        
        status = manager.check_capacity(memories)
        
        assert status["total_exceeded"]
    
    def test_get_memories_to_remove(self):
        """测试选择要移除的记忆"""
        manager = CapacityManager(max_per_level=1, max_total=10)
        
        memories = [
            {"id": "low1", "level": "long_term", "relevance_score": 0.1},
            {"id": "high1", "level": "long_term", "relevance_score": 0.9},
            {"id": "mid1", "level": "long_term", "relevance_score": 0.5},
        ]
        
        to_remove = manager.get_memories_to_remove(memories)
        
        assert len(to_remove) == 2
        assert "low1" in to_remove


class TestQualityCalculation:
    """质量计算测试"""
    
    def test_quality_with_high_usage(self):
        """测试高频使用提高质量"""
        service = MemoryForgetService()
        
        high_usage_quality = service._calculate_quality(
            relevance_score=0.5,
            usage_count=20,
            days_since_creation=30,
            days_since_access=5,
        )
        
        low_usage_quality = service._calculate_quality(
            relevance_score=0.5,
            usage_count=0,
            days_since_creation=30,
            days_since_access=5,
        )
        
        assert high_usage_quality > low_usage_quality
    
    def test_quality_decay_over_time(self):
        """测试质量随时间衰减"""
        service = MemoryForgetService()
        
        recent_quality = service._calculate_quality(
            relevance_score=0.8,
            usage_count=10,
            days_since_creation=1,
            days_since_access=1,
        )
        
        old_quality = service._calculate_quality(
            relevance_score=0.8,
            usage_count=10,
            days_since_creation=180,
            days_since_access=180,
        )
        
        assert recent_quality > old_quality


class TestIntegration:
    """集成测试"""
    
    def test_full_forget_workflow(self):
        """测试完整遗忘流程"""
        from app.services.memory.memory_forget import CapacityManager
        
        service = MemoryForgetService(
            ForgetPolicy(
                min_quality_threshold=0.3,
                not_accessed_days=30,
            )
        )
        cap_manager = CapacityManager(max_per_level=1, max_total=2)
        
        memories = [
            {
                "id": "forget_low_quality",
                "level": "working",
                "relevance_score": 0.1,
                "usage_count": 0,
                "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=60)).isoformat(),
            },
            {
                "id": "forget_not_accessed",
                "level": "short_term",
                "relevance_score": 0.5,
                "usage_count": 2,
                "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(days=100)).isoformat(),
            },
            {
                "id": "keep_important",
                "level": "working",
                "relevance_score": 0.7,
                "usage_count": 5,
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "last_accessed_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            },
        ]
        
        plan = service.get_forget_plan(memories, "test_agent")
        
        assert plan["candidate_count"] >= 2
        assert plan["candidate_count"] <= 3
        
        forget_ids = [c["memory_id"] for c in plan["candidates"]]
        assert "keep_important" not in forget_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
