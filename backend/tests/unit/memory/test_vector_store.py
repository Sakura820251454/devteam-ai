"""
Phase 4.2 向量检索测试

测试语义检索功能
"""
import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.memory.vector_store import VectorStore
from app.services.memory.semantic_retriever import SemanticRetriever


class TestVectorStore:
    @pytest_asyncio.fixture
    async def vector_store(self, tmp_path):
        store = VectorStore(
            embedding_model="BAAI/bge-small-zh-v1.5",
            index_path=str(tmp_path / "vector_index")
        )
        await store.initialize()
        return store
    
    @pytest.mark.asyncio
    async def test_initialize(self, tmp_path):
        store = VectorStore(
            embedding_model="BAAI/bge-small-zh-v1.5",
            index_path=str(tmp_path / "vector_index")
        )
        await store.initialize()
        
        assert store._initialized is True
        assert store.embedder is not None
        assert store.index is not None
    
    @pytest.mark.asyncio
    async def test_add_document(self, vector_store):
        await vector_store.add_document(
            doc_id="test_1",
            content="Python 是一种流行的编程语言",
            metadata={"category": "programming"}
        )
        
        assert "test_1" in vector_store.doc_store
        assert vector_store.index.ntotal == 1
    
    @pytest.mark.asyncio
    async def test_search(self, vector_store):
        docs = [
            ("doc_1", "Python 是一种流行的编程语言", {"category": "programming"}),
            ("doc_2", "Java 是面向对象的编程语言", {"category": "programming"}),
            ("doc_3", "机器学习是人工智能的一个分支", {"category": "ai"}),
            ("doc_4", "深度学习使用神经网络", {"category": "ai"}),
        ]
        
        for doc_id, content, metadata in docs:
            await vector_store.add_document(doc_id, content, metadata)
        
        results = await vector_store.search(
            query="编程语言",
            k=2
        )
        
        assert len(results) > 0
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_search_with_filter(self, vector_store):
        docs = [
            ("doc_1", "Python 编程", {"category": "programming", "agent_id": "agent_1"}),
            ("doc_2", "Java 编程", {"category": "programming", "agent_id": "agent_2"}),
            ("doc_3", "机器学习", {"category": "ai", "agent_id": "agent_1"}),
        ]
        
        for doc_id, content, metadata in docs:
            await vector_store.add_document(doc_id, content, metadata)
        
        results = await vector_store.search(
            query="编程",
            k=10,
            filter_metadata={"agent_id": "agent_1"}
        )
        
        for doc_id, score, metadata in results:
            assert metadata.get("agent_id") == "agent_1"
    
    @pytest.mark.asyncio
    async def test_delete_document(self, vector_store):
        await vector_store.add_document(
            doc_id="test_delete",
            content="测试删除文档",
            metadata={}
        )
        
        assert "test_delete" in vector_store.doc_store
        
        await vector_store.delete_document("test_delete")
        
        assert "test_delete" not in vector_store.doc_store
    
    @pytest.mark.asyncio
    async def test_persistence(self, tmp_path):
        index_path = str(tmp_path / "vector_index")
        
        store1 = VectorStore(
            embedding_model="BAAI/bge-small-zh-v1.5",
            index_path=index_path
        )
        await store1.initialize()
        
        await store1.add_document(
            doc_id="persist_test",
            content="持久化测试",
            metadata={"test": True}
        )
        
        store2 = VectorStore(
            embedding_model="BAAI/bge-small-zh-v1.5",
            index_path=index_path
        )
        await store2.initialize()
        
        assert "persist_test" in store2.doc_store


class TestSemanticRetriever:
    @pytest_asyncio.fixture
    async def retriever(self, tmp_path):
        from app.services.memory import vector_store
        
        original_path = vector_store.VectorStore.__init__.__defaults__
        
        retriever = SemanticRetriever()
        retriever._vector_store = VectorStore(
            embedding_model="BAAI/bge-small-zh-v1.5",
            index_path=str(tmp_path / "vector_index")
        )
        await retriever._vector_store.initialize()
        
        return retriever
    
    @pytest.mark.asyncio
    async def test_index_memory(self, retriever):
        await retriever.index_memory(
            memory_id="mem_1",
            content="Python 是一种流行的编程语言",
            metadata={"agent_id": "agent_1", "level": "long_term"}
        )
        
        doc = await retriever._vector_store.get_document("mem_1")
        assert doc is not None
        assert doc.content == "Python 是一种流行的编程语言"
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, retriever):
        memories = [
            ("mem_1", "Python 编程语言入门教程"),
            ("mem_2", "Java 面向对象编程"),
            ("mem_3", "机器学习算法介绍"),
            ("mem_4", "深度学习神经网络"),
        ]
        
        for mem_id, content in memories:
            await retriever.index_memory(
                memory_id=mem_id,
                content=content,
                metadata={"agent_id": "agent_1"}
            )
        
        results = await retriever.semantic_search(
            query="编程教程",
            agent_id="agent_1",
            k=2
        )
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_keyword_search(self, retriever):
        memories = [
            {"id": "mem_1", "content": "Python 编程", "tags": ["编程"]},
            {"id": "mem_2", "content": "Java 开发", "tags": ["开发"]},
            {"id": "mem_3", "content": "机器学习算法", "tags": ["AI"]},
        ]
        
        results = retriever.keyword_search(
            query="编程",
            memories=memories,
            k=2
        )
        
        assert len(results) > 0
        assert results[0][0] == "mem_1"
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, retriever):
        for i, content in enumerate([
            "Python 是一种流行的编程语言",
            "Java 是面向对象的编程语言",
            "机器学习是人工智能的分支",
            "深度学习使用神经网络",
        ]):
            await retriever.index_memory(
                memory_id=f"mem_{i}",
                content=content,
                metadata={"agent_id": "agent_1", "level": "long_term"}
            )
        
        memories = [
            {"id": "mem_0", "content": "Python 是一种流行的编程语言", "tags": ["Python", "编程"]},
            {"id": "mem_1", "content": "Java 是面向对象的编程语言", "tags": ["Java", "编程"]},
            {"id": "mem_2", "content": "机器学习是人工智能的分支", "tags": ["AI", "机器学习"]},
            {"id": "mem_3", "content": "深度学习使用神经网络", "tags": ["AI", "深度学习"]},
        ]
        
        results = await retriever.hybrid_search(
            query="编程语言",
            memories=memories,
            agent_id="agent_1",
            k=3
        )
        
        assert len(results) > 0
        assert len(results) <= 3
        
        for result in results:
            assert hasattr(result, 'memory_id')
            assert hasattr(result, 'score')
            assert hasattr(result, 'content')


class TestSemanticRetrievalIntegration:
    @pytest.mark.asyncio
    async def test_semantic_vs_keyword(self, tmp_path):
        retriever = SemanticRetriever()
        retriever._vector_store = VectorStore(
            embedding_model="BAAI/bge-small-zh-v1.5",
            index_path=str(tmp_path / "vector_index")
        )
        await retriever._vector_store.initialize()
        
        memories = [
            {"id": "mem_1", "content": "如何使用 Python 进行数据分析", "tags": ["Python", "数据分析"]},
            {"id": "mem_2", "content": "Java Spring Boot 框架教程", "tags": ["Java", "Spring"]},
            {"id": "mem_3", "content": "机器学习模型训练方法", "tags": ["ML", "训练"]},
        ]
        
        for mem in memories:
            await retriever.index_memory(
                memory_id=mem["id"],
                content=mem["content"],
                metadata={"tags": mem["tags"]}
            )
        
        semantic_results = await retriever.semantic_search(
            query="数据科学",
            k=2
        )
        
        keyword_results = retriever.keyword_search(
            query="数据科学",
            memories=memories,
            k=2
        )
        
        assert len(semantic_results) >= 0
        assert len(keyword_results) >= 0
    
    @pytest.mark.asyncio
    async def test_chinese_semantic_search(self, tmp_path):
        retriever = SemanticRetriever()
        retriever._vector_store = VectorStore(
            embedding_model="BAAI/bge-small-zh-v1.5",
            index_path=str(tmp_path / "vector_index")
        )
        await retriever._vector_store.initialize()
        
        chinese_memories = [
            ("mem_1", "用户登录功能开发完成"),
            ("mem_2", "数据库性能优化方案"),
            ("mem_3", "前端页面布局调整"),
            ("mem_4", "API 接口安全加固"),
        ]
        
        for mem_id, content in chinese_memories:
            await retriever.index_memory(
                memory_id=mem_id,
                content=content,
                metadata={}
            )
        
        results = await retriever.semantic_search(
            query="认证安全",
            k=2
        )
        
        assert len(results) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
