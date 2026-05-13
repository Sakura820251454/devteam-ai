"""
批处理与重试服务 - Phase 4 优化

提供：
- 记忆批量操作
- 带重试机制的向量操作
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, TypeVar
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on_exceptions: tuple = (Exception,),
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_exceptions = retry_on_exceptions


class BatchProcessor:
    """
    批处理器
    
    提供批量记忆操作优化
    """
    
    def __init__(self, batch_size: int = 100, max_concurrent: int = 10):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(
        self,
        items: List[Any],
        process_fn: Callable,
        on_error: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        批量处理项目
        
        Args:
            items: 待处理项目列表
            process_fn: 处理函数，接收单个项目
            on_error: 错误处理函数
            
        Returns:
            处理结果统计
        """
        results = {
            "total": len(items),
            "success": 0,
            "failed": 0,
            "errors": [],
        }
        
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        for batch in batches:
            tasks = []
            for item in batch:
                async with self._semaphore:
                    task = self._process_item(item, process_fn, on_error)
                    tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results["failed"] += 1
                    results["errors"].append({
                        "item": str(batch[i])[:100],
                        "error": str(result),
                    })
                else:
                    results["success"] += 1
        
        return results
    
    async def _process_item(
        self,
        item: Any,
        process_fn: Callable,
        on_error: Optional[Callable],
    ) -> Any:
        """处理单个项目"""
        try:
            if asyncio.iscoroutinefunction(process_fn):
                return await process_fn(item)
            else:
                return process_fn(item)
        except Exception as e:
            if on_error:
                on_error(item, e)
            raise


class RetryableOperation:
    """
    可重试操作包装器
    
    为不稳定操作添加自动重试
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    async def execute(
        self,
        operation: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        执行带重试的操作
        
        Args:
            operation: 异步操作函数
            *args, **kwargs: 操作参数
            
        Returns:
            操作结果
            
        Raises:
            最后一次尝试的异常
        """
        last_exception = None
        delay = self.config.initial_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)
                    
            except self.config.retry_on_exceptions as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.config.exponential_base,
                        self.config.max_delay
                    )
                else:
                    logger.error(
                        f"All {self.config.max_retries + 1} attempts failed"
                    )
        
        if last_exception:
            raise last_exception
    
    def with_retry(self, operation: Callable) -> Callable:
        """
        装饰器形式添加重试
        
        用法:
        ```python
        @retry_ops.with_retry
        async def unstable_operation():
            ...
        ```
        """
        @wraps(operation)
        async def wrapper(*args, **kwargs):
            return await self.execute(operation, *args, **kwargs)
        return wrapper


retry_ops = RetryableOperation()


class VectorOperationRetry:
    """
    向量操作重试包装器
    
    为向量存储操作添加重试和降级机制
    """
    
    def __init__(self):
        self.retry_config = RetryConfig(
            max_retries=3,
            initial_delay=0.5,
            max_delay=10.0,
        )
        self.retry_ops = RetryableOperation(self.retry_config)
        self._fallback_mode = False
    
    async def add_with_retry(
        self,
        vector_store,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """添加向量（带重试）"""
        try:
            return await self.retry_ops.execute(
                vector_store.add_document,
                doc_id=doc_id,
                content=content,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to add vector after retries: {e}")
            self._fallback_mode = True
            return False
    
    async def search_with_fallback(
        self,
        vector_store,
        query: str,
        k: int = 10,
        filter_metadata: Optional[Dict] = None,
    ) -> List:
        """
        搜索（失败时降级到关键词搜索）
        """
        if self._fallback_mode:
            logger.info("Vector search unavailable, using keyword fallback")
            return []
        
        try:
            return await self.retry_ops.execute(
                vector_store.search,
                query=query,
                k=k,
                filter_metadata=filter_metadata,
            )
        except Exception as e:
            logger.warning(f"Vector search failed: {e}. Falling back to keyword.")
            self._fallback_mode = True
            return []
    
    def reset_fallback(self):
        """重置降级模式"""
        self._fallback_mode = False


vector_retry = VectorOperationRetry()


class MemoryBatchService:
    """
    记忆批处理服务
    
    提供高效的批量记忆操作
    """
    
    def __init__(self, db=None):
        self.db = db
        self.processor = BatchProcessor(batch_size=50, max_concurrent=5)
        self.vector_retry = vector_retry
    
    async def batch_add_memories(
        self,
        memories: List[Dict[str, Any]],
        db_session,
        vector_store=None,
    ) -> Dict[str, Any]:
        """
        批量添加记忆
        
        Args:
            memories: 记忆列表
            db_session: 数据库会话
            vector_store: 可选，向量存储
        """
        from app.services.memory.persistent_memory_manager import PersistentMemoryManager
        
        async def add_single(memory_data):
            manager = PersistentMemoryManager(db_session)
            result = await manager.add_memory(**memory_data)
            
            if vector_store and result:
                await self.vector_retry.add_with_retry(
                    vector_store,
                    doc_id=result.id,
                    content=result.content,
                    metadata={
                        "agent_id": memory_data.get("agent_id"),
                        "level": result.level,
                        "tags": result.tags,
                    }
                )
            
            return result
        
        results = await self.processor.process_batch(memories, add_single)
        return results
    
    async def batch_index_memories(
        self,
        memories: List[Dict[str, Any]],
        vector_store,
    ) -> Dict[str, Any]:
        """批量索引记忆到向量库"""
        async def index_single(memory):
            await self.vector_retry.add_with_retry(
                vector_store,
                doc_id=memory["id"],
                content=memory["content"],
                metadata=memory.get("metadata", {}),
            )
            return True
        
        return await self.processor.process_batch(memories, index_single)
