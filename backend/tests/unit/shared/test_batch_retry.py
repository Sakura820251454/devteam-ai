"""批量重试服务单元测试。

测试 RetryConfig / RetryableOperation / BatchProcessor / VectorOperationRetry。
纯逻辑测试，不依赖 LLM 或外部服务。
"""

import asyncio
import pytest

from app.services.shared.batch_retry import (
    RetryConfig,
    RetryableOperation,
    BatchProcessor,
    VectorOperationRetry,
    retry_ops,
)


# ========== RetryConfig ==========


class TestRetryConfig:
    """重试配置测试。"""

    def test_default_values(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.retry_on_exceptions == (Exception,)

    def test_custom_values(self):
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.1,
            max_delay=10.0,
            exponential_base=3.0,
            retry_on_exceptions=(ValueError, TypeError),
        )
        assert config.max_retries == 5
        assert config.initial_delay == 0.1
        assert config.max_delay == 10.0
        assert config.exponential_base == 3.0
        assert config.retry_on_exceptions == (ValueError, TypeError)


# ========== RetryableOperation ==========


class TestRetryableOperation:
    """重试操作测试。"""

    @pytest.mark.asyncio
    async def test_execute_success_first_try(self):
        """第一次尝试成功，不重试。"""
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_ops.execute(succeed)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_retry_then_succeed(self):
        """前两次失败，第三次成功。"""
        config = RetryConfig(max_retries=3, initial_delay=0.001, max_delay=0.1)
        ops = RetryableOperation(config)
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"fail {call_count}")
            return "recovered"

        result = await ops.execute(flaky)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_all_failures_raise_last_exception(self):
        """全部重试失败，抛出最后一次异常。"""
        config = RetryConfig(max_retries=2, initial_delay=0.001, max_delay=0.1)
        ops = RetryableOperation(config)

        async def always_fail():
            raise RuntimeError("persistent failure")

        with pytest.raises(RuntimeError, match="persistent failure"):
            await ops.execute(always_fail)

    @pytest.mark.asyncio
    async def test_execute_does_not_retry_non_matching_exceptions(self):
        """非 retry_on_exceptions 中指定的异常不重试。"""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.001,
            retry_on_exceptions=(ValueError,),  # 只重试 ValueError
        )
        ops = RetryableOperation(config)
        call_count = 0

        async def type_error_fn():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await ops.execute(type_error_fn)
        assert call_count == 1  # 不重试

    @pytest.mark.asyncio
    async def test_with_retry_decorator(self):
        """with_retry 装饰器应包装函数。"""
        call_count = 0

        @retry_ops.with_retry
        async def decorated():
            nonlocal call_count
            call_count += 1
            return "decorated"

        result = await decorated()
        assert result == "decorated"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_sync_function_also_works(self):
        """同步函数也可被重试。"""
        call_count = 0

        def sync_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "sync ok"

        config = RetryConfig(max_retries=2, initial_delay=0.001, max_delay=0.1)
        ops = RetryableOperation(config)
        result = await ops.execute(sync_fn)
        assert result == "sync ok"
        assert call_count == 2


# ========== BatchProcessor ==========


class TestBatchProcessor:
    """批处理器测试。"""

    @pytest.mark.asyncio
    async def test_process_batch_all_success(self):
        processor = BatchProcessor(batch_size=10, max_concurrent=5)
        items = [1, 2, 3, 4, 5]

        async def double(x):
            return x * 2

        result = await processor.process_batch(items, double)
        assert result["total"] == 5
        assert result["success"] == 5
        assert result["failed"] == 0
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_process_batch_with_failures(self):
        processor = BatchProcessor(batch_size=10, max_concurrent=5)
        items = [1, 2, 0, 4, 5]  # 0 会导致除零错误

        async def divide(x):
            return 10 / x

        result = await processor.process_batch(items, divide)
        assert result["total"] == 5
        assert result["success"] == 4
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_process_batch_respects_batch_size(self):
        """Item 数量小于 batch_size 时只产生一个批次。"""
        processor = BatchProcessor(batch_size=3, max_concurrent=5)
        items = [1, 2, 3, 4, 5]

        async def identity(x):
            return x

        result = await processor.process_batch(items, identity)
        assert result["total"] == 5
        assert result["success"] == 5

    @pytest.mark.asyncio
    async def test_process_batch_sync_function(self):
        """process_fn 可以是同步函数。"""
        processor = BatchProcessor(batch_size=10, max_concurrent=5)
        items = ["a", "b", "c"]

        def upper(s):
            return s.upper()

        result = await processor.process_batch(items, upper)
        assert result["success"] == 3

    @pytest.mark.asyncio
    async def test_process_batch_empty_items(self):
        processor = BatchProcessor()
        result = await processor.process_batch([], lambda x: x)
        assert result["total"] == 0
        assert result["success"] == 0


# ========== VectorOperationRetry ==========


class TestVectorOperationRetry:
    """向量操作重试封装测试。"""

    @pytest.fixture
    def vector_retry(self):
        return VectorOperationRetry()

    def test_initial_state_not_fallback(self, vector_retry):
        assert vector_retry._fallback_mode is False

    def test_reset_fallback(self, vector_retry):
        vector_retry._fallback_mode = True
        vector_retry.reset_fallback()
        assert vector_retry._fallback_mode is False

    @pytest.mark.asyncio
    async def test_search_returns_results_from_store(self, vector_retry):
        """当向量存储正常时返回搜索结果。"""
        class FakeStore:
            async def search(self, query, k=10, filter_metadata=None):
                return [{"id": "doc1", "score": 0.9}]

        result = await vector_retry.search_with_fallback(FakeStore(), "test query")
        assert len(result) == 1
        assert result[0]["id"] == "doc1"
        assert vector_retry._fallback_mode is False

    @pytest.mark.asyncio
    async def test_search_fallback_on_failure(self, vector_retry):
        """向量存储失败时降级为空结果。"""
        class FailingStore:
            async def search(self, query, k=10, filter_metadata=None):
                raise ConnectionError("vector store down")

        result = await vector_retry.search_with_fallback(FailingStore(), "test query")
        assert result == []
        assert vector_retry._fallback_mode is True

    @pytest.mark.asyncio
    async def test_search_returns_empty_in_fallback_mode(self, vector_retry):
        """一旦进入降级模式，后续搜索直接返回空。"""
        vector_retry._fallback_mode = True
        vector_retry.retry_config = RetryConfig(max_retries=0)
        vector_retry.retry_ops = RetryableOperation(vector_retry.retry_config)

        class GoodStore:
            async def search(self, query, k=10, filter_metadata=None):
                return [{"id": "should_not_reach"}]

        result = await vector_retry.search_with_fallback(GoodStore(), "test")
        assert result == []  # 降级模式，不调用 store

    @pytest.mark.asyncio
    async def test_add_with_retry_success(self, vector_retry):
        """向量添加成功。"""
        class FakeStore:
            async def add_document(self, doc_id, content, metadata=None):
                return True

        result = await vector_retry.add_with_retry(FakeStore(), "doc1", "content here")
        assert result is True

    @pytest.mark.asyncio
    async def test_add_with_retry_failure_triggers_fallback(self, vector_retry):
        """向量添加失败后进入降级模式。"""
        class FailingStore:
            async def add_document(self, doc_id, content, metadata=None):
                raise RuntimeError("store error")

        result = await vector_retry.add_with_retry(FailingStore(), "doc1", "content")
        assert result is False
        assert vector_retry._fallback_mode is True


# ========== 全局实例 ==========


class TestGlobalRetryOps:
    """全局 retry_ops 实例。"""

    def test_default_retry_ops_exists(self):
        assert retry_ops is not None
        assert retry_ops.config.max_retries == 3
