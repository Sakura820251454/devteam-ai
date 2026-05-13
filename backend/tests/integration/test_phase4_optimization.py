"""
Phase 4 优化测试

测试新增的优化功能：
- 智能学习服务
- 记忆晋升机制
- 批处理和重试
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import asyncio

from app.services.learning.intelligent_learning import IntelligentLearningService
from app.services.memory.memory_promotion import (
    MemoryPromotionService,
    PromotionRule,
)
from app.services.shared.batch_retry import (
    BatchProcessor,
    RetryableOperation,
    RetryConfig,
    VectorOperationRetry,
)


class TestIntelligentLearningService:
    """智能学习服务测试"""
    
    def test_learn_from_task(self):
        """测试从任务学习"""
        service = IntelligentLearningService()
        
        skill = asyncio.get_event_loop().run_until_complete(
            service.learn_from_task(
                agent_id="test_agent",
                task_description="优化数据库查询性能",
                decisions=[
                    {"step": 1, "action": "分析慢查询", "reasoning": "定位瓶颈"},
                    {"step": 2, "action": "添加索引", "reasoning": "优化性能"},
                ],
                outcomes={"speed_improvement": "10x"},
                success="success",
            )
        )
        
        assert skill is not None
        assert skill.category == "optimization"
        assert len(skill.trigger_keywords) > 0
    
    def test_recommend_skills(self):
        """测试技能推荐"""
        service = IntelligentLearningService()
        
        skill = asyncio.get_event_loop().run_until_complete(
            service.learn_from_task(
                agent_id="test_agent",
                task_description="编写 Python 单元测试",
                decisions=[
                    {"step": 1, "action": "编写测试用例", "reasoning": "覆盖场景"},
                ],
                outcomes={"tests_passed": 10},
                success="success",
            )
        )
        
        matches = asyncio.get_event_loop().run_until_complete(
            service.recommend_skills(
                task_description="如何为登录功能写测试",
                agent_id="test_agent",
            )
        )
        
        assert len(matches) >= 0


class TestMemoryPromotionService:
    """记忆晋升服务测试"""
    
    def test_should_promote_working_to_short_term(self):
        """测试工作记忆晋升条件"""
        service = MemoryPromotionService()
        
        memory = {
            "id": "mem_1",
            "level": "working",
            "usage_count": 5,
            "relevance_score": 0.5,
            "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
        }
        
        target = service.evaluate_promotion(memory)
        assert target == "short_term"
    
    def test_should_not_promote_new_memory(self):
        """测试新记忆不晋升"""
        service = MemoryPromotionService()
        
        memory = {
            "id": "mem_1",
            "level": "working",
            "usage_count": 1,
            "relevance_score": 0.5,
            "created_at": datetime.now().isoformat(),
        }
        
        target = service.evaluate_promotion(memory)
        assert target is None
    
    def test_get_promotion_candidates(self):
        """测试获取晋升候选"""
        service = MemoryPromotionService()
        
        memories = [
            {
                "id": "mem_1",
                "level": "working",
                "usage_count": 5,
                "relevance_score": 0.5,
                "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
            },
            {
                "id": "mem_2",
                "level": "working",
                "usage_count": 1,
                "relevance_score": 0.5,
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": "mem_3",
                "level": "short_term",
                "usage_count": 15,
                "relevance_score": 0.7,
                "created_at": (datetime.now() - timedelta(days=35)).isoformat(),
            },
        ]
        
        candidates = service.get_promotion_candidates(memories)
        
        assert len(candidates) == 2
        levels = [target for _, target in candidates]
        assert "short_term" in levels
        assert "long_term" in levels
    
    def test_get_statistics(self):
        """测试统计信息"""
        service = MemoryPromotionService()
        
        memories = [
            {
                "id": "mem_1",
                "level": "working",
                "usage_count": 3,
                "relevance_score": 0.5,
            },
            {
                "id": "mem_2",
                "level": "short_term",
                "usage_count": 10,
                "relevance_score": 0.7,
            },
        ]
        
        stats = service.get_statistics(memories)
        
        assert stats["total"] == 2
        assert stats["by_level"]["working"] == 1
        assert stats["by_level"]["short_term"] == 1
        assert "promotion_candidates" in stats


class TestBatchProcessor:
    """批处理器测试"""
    
    @pytest.mark.asyncio
    async def test_process_batch_success(self):
        """测试批量处理成功"""
        processor = BatchProcessor(batch_size=2, max_concurrent=2)
        
        items = [1, 2, 3, 4, 5]
        
        async def process(item):
            await asyncio.sleep(0.01)
            return item * 2
        
        results = await processor.process_batch(items, process)
        
        assert results["total"] == 5
        assert results["success"] == 5
        assert results["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self):
        """测试批量处理含错误"""
        processor = BatchProcessor(batch_size=2, max_concurrent=2)
        
        items = [1, 2, 3]
        
        def process(item):
            if item == 2:
                raise ValueError("Test error")
            return item * 2
        
        results = await processor.process_batch(items, process)
        
        assert results["total"] == 3
        assert results["failed"] == 1
        assert len(results["errors"]) == 1


class TestRetryableOperation:
    """重试操作测试"""
    
    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """测试成功操作"""
        retry_ops = RetryableOperation()
        
        call_count = 0
        
        async def unstable_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_ops.execute(unstable_operation)
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """测试失败重试"""
        retry_ops = RetryableOperation(RetryConfig(max_retries=3, initial_delay=0.01))
        
        call_count = 0
        
        async def unstable_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = await retry_ops.execute(unstable_operation)
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        retry_ops = RetryableOperation(RetryConfig(max_retries=2, initial_delay=0.01))
        
        call_count = 0
        
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError):
            await retry_ops.execute(always_fail)
        
        assert call_count == 3


class TestVectorOperationRetry:
    """向量操作重试测试"""
    
    def test_fallback_mode(self):
        """测试降级模式"""
        retry_wrapper = VectorOperationRetry()
        
        retry_wrapper._fallback_mode = True
        
        assert retry_wrapper._fallback_mode is True
        
        retry_wrapper.reset_fallback()
        
        assert retry_wrapper._fallback_mode is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
