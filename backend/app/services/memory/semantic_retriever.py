"""
语义检索服务 - Phase 4.2

结合向量检索和关键词检索的混合检索
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.services.memory.vector_store import VectorStore, get_vector_store


@dataclass
class SearchResult:
    memory_id: str
    content: str
    score: float
    level: str
    tags: List[str]
    metadata: Dict


class SemanticRetriever:
    def __init__(
        self,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self._vector_store: Optional[VectorStore] = None
    
    async def initialize(self):
        if self._vector_store is None:
            self._vector_store = await get_vector_store()
    
    async def index_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        if not self._vector_store:
            await self.initialize()
        
        await self._vector_store.add_document(
            doc_id=memory_id,
            content=content,
            metadata=metadata or {}
        )
    
    async def remove_from_index(self, memory_id: str):
        if not self._vector_store:
            await self.initialize()
        
        await self._vector_store.delete_document(memory_id)
    
    async def semantic_search(
        self,
        query: str,
        agent_id: Optional[str] = None,
        k: int = 10
    ) -> List[Tuple[str, float, Dict]]:
        if not self._vector_store:
            await self.initialize()
        
        filter_metadata = None
        if agent_id:
            filter_metadata = {"agent_id": agent_id}
        
        return await self._vector_store.search(
            query=query,
            k=k,
            filter_metadata=filter_metadata
        )
    
    def keyword_search(
        self,
        query: str,
        memories: List[Dict],
        k: int = 10
    ) -> List[Tuple[str, float, Dict]]:
        query_lower = query.lower()
        keywords = set(query_lower.split())
        
        results = []
        for mem in memories:
            score = 0.0
            
            tags = mem.get("tags", [])
            for tag in tags:
                if tag.lower() in query_lower:
                    score += 2.0
            
            content_lower = mem.get("content", "").lower()
            for keyword in keywords:
                if keyword in content_lower:
                    score += 1.0
            
            if score > 0:
                results.append((mem.get("id"), score, mem))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]
    
    async def hybrid_search(
        self,
        query: str,
        memories: List[Dict],
        agent_id: Optional[str] = None,
        k: int = 10
    ) -> List[SearchResult]:
        await self.initialize()
        
        vector_results = await self.semantic_search(
            query=query,
            agent_id=agent_id,
            k=k * 2
        )
        
        keyword_results = self.keyword_search(
            query=query,
            memories=memories,
            k=k * 2
        )
        
        combined_scores: Dict[str, Dict] = {}
        
        max_vector_score = max((score for _, score, _ in vector_results), default=1.0)
        for memory_id, score, metadata in vector_results:
            normalized_score = score / max_vector_score if max_vector_score > 0 else 0
            combined_scores[memory_id] = {
                "vector_score": normalized_score,
                "keyword_score": 0.0,
                "metadata": metadata
            }
        
        max_keyword_score = max((score for _, score, _ in keyword_results), default=1.0)
        for memory_id, score, metadata in keyword_results:
            normalized_score = score / max_keyword_score if max_keyword_score > 0 else 0
            if memory_id in combined_scores:
                combined_scores[memory_id]["keyword_score"] = normalized_score
            else:
                combined_scores[memory_id] = {
                    "vector_score": 0.0,
                    "keyword_score": normalized_score,
                    "metadata": metadata
                }
        
        final_results = []
        for memory_id, scores in combined_scores.items():
            hybrid_score = (
                self.vector_weight * scores["vector_score"] +
                self.keyword_weight * scores["keyword_score"]
            )
            
            metadata = scores["metadata"]
            final_results.append(SearchResult(
                memory_id=memory_id,
                content=metadata.get("content", ""),
                score=hybrid_score,
                level=metadata.get("level", "working"),
                tags=metadata.get("tags", []),
                metadata=metadata
            ))
        
        final_results.sort(key=lambda x: x.score, reverse=True)
        return final_results[:k]


semantic_retriever: Optional[SemanticRetriever] = None


async def get_semantic_retriever() -> SemanticRetriever:
    global semantic_retriever
    if semantic_retriever is None:
        semantic_retriever = SemanticRetriever()
        await semantic_retriever.initialize()
    return semantic_retriever
