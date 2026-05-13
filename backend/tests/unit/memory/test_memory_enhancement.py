"""
记忆高级优化测试

测试记忆系统的深度优化功能
"""

import pytest
from datetime import datetime, timedelta

from app.services.memory.memory_enhancement import (
    MemoryDecayEngine,
    MemoryDeduplicator,
    MemoryPrivacyEngine,
    MemoryEnhancementService,
    memory_enhancer,
)


class TestMemoryDecayEngine:
    """记忆衰减引擎测试"""
    
    def test_basic_decay(self):
        """测试基础衰减"""
        engine = MemoryDecayEngine(halflife_days=30)
        
        score = engine.calculate_decayed_score(1.0, 30)
        assert score == pytest.approx(0.5, 0.01)
        
        score = engine.calculate_decayed_score(1.0, 60)
        assert score == pytest.approx(0.25, 0.01)
    
    def test_usage_bonus(self):
        """测试使用频率奖励"""
        engine = MemoryDecayEngine(halflife_days=30)
        
        score_without = engine.calculate_decayed_score(1.0, 30, usage_count=0)
        score_with = engine.calculate_decayed_score(1.0, 30, usage_count=10)
        
        assert score_with > score_without
        assert score_with <= 1.0
    
    def test_min_score(self):
        """测试最小分数限制"""
        engine = MemoryDecayEngine(halflife_days=30, min_score=0.1)
        
        score = engine.calculate_decayed_score(1.0, 365)
        assert score >= 0.1
    
    def test_freshness_calculation(self):
        """测试新鲜度计算"""
        engine = MemoryDecayEngine()
        
        now = datetime.now()
        recent = now - timedelta(hours=2)
        freshness = engine.calculate_freshness(recent, recent)
        assert freshness > 0.99
        
        old = now - timedelta(days=120)
        freshness = engine.calculate_freshness(old, old)
        assert freshness < 1.0


class TestMemoryDeduplicator:
    """记忆去重器测试"""
    
    def test_content_hash(self):
        """测试内容哈希"""
        dedup = MemoryDeduplicator()
        
        hash1 = dedup.compute_content_hash("Hello World")
        hash2 = dedup.compute_content_hash("Hello   World  ")
        
        assert hash1 == hash2
    
    def test_similarity_calculation(self):
        """测试相似度计算"""
        dedup = MemoryDeduplicator()
        
        # 高相似度
        sim_high = dedup.compute_similarity(
            "Python is a great language for programming",
            "Python is a great language for programming",
        )
        assert sim_high >= 0.7
        
        # 中等相似度
        sim_mid = dedup.compute_similarity(
            "Python is a great language for programming",
            "Python is good for programming"
        )
        assert sim_mid > 0.2
        
        # 低相似度
        sim_low = dedup.compute_similarity(
            "Python is great",
            "Java is great"
        )
        assert sim_low < 0.8
    
    def test_tag_similarity(self):
        """测试标签相似度"""
        dedup = MemoryDeduplicator()
        
        sim = dedup._tag_similarity(
            ["python", "programming"],
            ["python", "coding"]
        )
        assert sim > 0.3
    
    def test_find_duplicates(self):
        """测试查找重复记忆"""
        dedup = MemoryDeduplicator()
        
        memories = [
            {"id": "1", "content": "This is a test", "tags": ["test"]},
            {"id": "2", "content": "This is a test", "tags": ["test"]},
            {"id": "3", "content": "Different content", "tags": ["other"]},
        ]
        
        duplicates = dedup.find_duplicates(memories)
        
        assert len(duplicates) == 1
        assert len(duplicates[0]) == 2
    
    def test_merge_strategies(self):
        """测试合并策略"""
        dedup = MemoryDeduplicator()
        
        memories = [
            {"id": "1", "content": "Version 1", "tags": ["a"], "usage_count": 2},
            {"id": "2", "content": "Version 2", "tags": ["b"], "usage_count": 5},
        ]
        
        merged_newest = dedup.merge_memories(memories, strategy="newest")
        assert merged_newest["content"] == "Version 1"
        
        merged_combined = dedup.merge_memories(memories, strategy="combined")
        assert set(merged_combined["tags"]) == {"a", "b"}
        assert merged_combined["usage_count"] == 7


class TestMemoryPrivacyEngine:
    """记忆隐私引擎测试"""
    
    def test_sensitive_content_detection(self):
        """测试敏感内容检测"""
        engine = MemoryPrivacyEngine()
        
        # 测试密码检测
        detections = engine.detect_sensitive_content("password=secret123")
        assert any(d["type"] == "secret" for d in detections)
        
        # 测试API key检测
        detections = engine.detect_sensitive_content("api_key=abc123xyz")
        assert any(d["type"] == "credential" for d in detections)
        
        # 测试邮箱检测
        detections = engine.detect_sensitive_content("contact@example.com")
        assert any(d["type"] == "email" for d in detections)
    
    def test_sensitive_mark(self):
        """测试敏感标记"""
        engine = MemoryPrivacyEngine()
        
        mem_data = {"content": "api_key=test123", "other": "data"}
        result = engine.mark_sensitive(mem_data)
        
        assert result.get("_sensitive") is True
        assert "credential" in result.get("_sensitive_types", [])


class TestMemoryEnhancementService:
    """记忆增强综合服务测试"""
    
    def test_enhance_memory(self):
        """测试记忆增强"""
        service = MemoryEnhancementService()
        
        mem = {
            "content": "Normal memory content",
            "created_at": datetime.now() - timedelta(days=10),
            "last_accessed_at": datetime.now() - timedelta(days=1),
            "usage_count": 5,
            "relevance_score": 0.8,
        }
        
        enhanced = service.enhance_memory(mem)
        
        assert "_quality" in enhanced
        assert "freshness" in enhanced["_quality"]
        assert "relevance" in enhanced["_quality"]
        assert "utility" in enhanced["_quality"]
        assert "overall" in enhanced["_quality"]
    
    def test_calculate_quality(self):
        """测试质量计算"""
        service = MemoryEnhancementService()
        
        mem = {
            "created_at": datetime.now() - timedelta(days=10),
            "last_accessed_at": datetime.now() - timedelta(days=1),
            "usage_count": 5,
            "relevance_score": 0.8,
        }
        
        quality = service.calculate_quality(mem)
        
        assert 0 <= quality.freshness_score <= 1
        assert 0 <= quality.relevance_score <= 1
        assert 0 <= quality.utility_score <= 1
        assert 0 <= quality.overall_quality <= 1
    
    def test_refresh_memories(self):
        """测试批处理记忆刷新"""
        service = MemoryEnhancementService()
        
        memories = [
            {"content": "Mem 1", "created_at": datetime.now()},
            {"content": "Mem 2: password=secret", "created_at": datetime.now()},
        ]
        
        refreshed = service.refresh_memories(memories)
        
        assert len(refreshed) == 2
        for m in refreshed:
            assert "_quality" in m


class TestFullMemoryPipeline:
    """完整记忆优化流程测试"""
    
    def test_enhancement_pipeline(self):
        """测试完整的增强流程"""
        # 1. 模拟原始记忆
        memories = [
            {
                "id": "m1",
                "content": "Python is a great programming language",
                "tags": ["python", "programming"],
                "created_at": datetime.now() - timedelta(days=15),
                "usage_count": 8,
                "relevance_score": 0.9,
            },
            {
                "id": "m2",
                "content": "Python is a great programming language",
                "tags": ["python"],
                "created_at": datetime.now() - timedelta(days=10),
                "usage_count": 3,
                "relevance_score": 0.7,
            },
            {
                "id": "m3",
                "content": "Password: mysecret123",
                "tags": ["private"],
                "created_at": datetime.now() - timedelta(days=5),
                "usage_count": 1,
                "relevance_score": 0.5,
            },
        ]
        
        # 2. 增强
        enhanced = memory_enhancer.refresh_memories(memories)
        
        # 3. 检查质量评分
        for m in enhanced:
            assert "_quality" in m
        
        # 4. 检查敏感标记
        sensitive = [m for m in enhanced if m.get("_sensitive")]
        assert len(sensitive) == 1
        
        # 5. 检查去重
        duplicates = memory_enhancer.deduplicator.find_duplicates(enhanced)
        assert len(duplicates) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
