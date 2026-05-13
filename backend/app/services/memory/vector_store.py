"""
向量存储服务 - Phase 4.2

使用 FAISS 进行向量检索，支持语义相似度搜索
"""
import os
import json
import pickle
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import faiss
from sentence_transformers import SentenceTransformer


@dataclass
class VectorDocument:
    id: str
    content: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)


class VectorStore:
    def __init__(
        self,
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
        index_path: str = "./data/vector_index",
        dimension: int = 512
    ):
        self.embedding_model_name = embedding_model
        self.index_path = index_path
        self.dimension = dimension
        
        self.embedder: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.IndexFlatIP] = None
        self.doc_store: Dict[str, VectorDocument] = {}
        self.id_to_idx: Dict[str, int] = {}
        self.idx_to_id: Dict[int, str] = {}
        self.next_idx: int = 0
        
        self._initialized = False
    
    async def initialize(self):
        if self._initialized:
            return
        
        self.embedder = SentenceTransformer(self.embedding_model_name)
        actual_dim = self.embedder.get_sentence_embedding_dimension()
        if actual_dim != self.dimension:
            self.dimension = actual_dim
        
        self.index = faiss.IndexFlatIP(self.dimension)
        
        os.makedirs(self.index_path, exist_ok=True)
        self._load_index()
        
        self._initialized = True
    
    def _load_index(self):
        index_file = os.path.join(self.index_path, "faiss.index")
        meta_file = os.path.join(self.index_path, "metadata.pkl")
        
        if os.path.exists(index_file) and os.path.exists(meta_file):
            try:
                self.index = faiss.read_index(index_file)
                with open(meta_file, "rb") as f:
                    data = pickle.load(f)
                    self.doc_store = data.get("doc_store", {})
                    self.id_to_idx = data.get("id_to_idx", {})
                    self.idx_to_id = data.get("idx_to_id", {})
                    self.next_idx = data.get("next_idx", 0)
            except Exception:
                self.index = faiss.IndexFlatIP(self.dimension)
    
    def _save_index(self):
        index_file = os.path.join(self.index_path, "faiss.index")
        meta_file = os.path.join(self.index_path, "metadata.pkl")
        
        faiss.write_index(self.index, index_file)
        with open(meta_file, "wb") as f:
            pickle.dump({
                "doc_store": self.doc_store,
                "id_to_idx": self.id_to_idx,
                "idx_to_id": self.idx_to_id,
                "next_idx": self.next_idx
            }, f)
    
    def _get_embedding(self, text: str) -> np.ndarray:
        if not self.embedder:
            raise RuntimeError("VectorStore not initialized. Call initialize() first.")
        
        embedding = self.embedder.encode(text, normalize_embeddings=True)
        return embedding.astype(np.float32)
    
    async def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        if not self._initialized:
            await self.initialize()
        
        if doc_id in self.doc_store:
            await self.update_document(doc_id, content, metadata)
            return True
        
        embedding = self._get_embedding(content)
        
        doc = VectorDocument(
            id=doc_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {}
        )
        
        self.doc_store[doc_id] = doc
        self.id_to_idx[doc_id] = self.next_idx
        self.idx_to_id[self.next_idx] = doc_id
        
        self.index.add(np.array([embedding]))
        self.next_idx += 1
        
        self._save_index()
        return True
    
    async def update_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        if doc_id not in self.doc_store:
            return False
        
        old_idx = self.id_to_idx[doc_id]
        
        embedding = self._get_embedding(content)
        
        doc = VectorDocument(
            id=doc_id,
            content=content,
            embedding=embedding,
            metadata=metadata or self.doc_store[doc_id].metadata
        )
        
        self.doc_store[doc_id] = doc
        self.index.reconstruct(old_idx)
        
        faiss_id_map = faiss.IDMap()
        faiss_id_map.add_with_ids(np.array([embedding]), np.array([old_idx]))
        
        self._save_index()
        return True
    
    async def delete_document(self, doc_id: str) -> bool:
        if doc_id not in self.doc_store:
            return False
        
        del self.doc_store[doc_id]
        del self.id_to_idx[doc_id]
        
        self._save_index()
        return True
    
    async def search(
        self,
        query: str,
        k: int = 10,
        filter_metadata: Optional[Dict] = None
    ) -> List[Tuple[str, float, Dict]]:
        if not self._initialized:
            await self.initialize()
        
        if self.index.ntotal == 0:
            return []
        
        query_embedding = self._get_embedding(query)
        
        search_k = min(k * 3, self.index.ntotal)
        distances, indices = self.index.search(np.array([query_embedding]), search_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            
            doc_id = self.idx_to_id.get(idx)
            if not doc_id or doc_id not in self.doc_store:
                continue
            
            doc = self.doc_store[doc_id]
            
            if filter_metadata:
                match = all(
                    doc.metadata.get(key) == value
                    for key, value in filter_metadata.items()
                )
                if not match:
                    continue
            
            results.append((doc_id, float(dist), doc.metadata))
            
            if len(results) >= k:
                break
        
        return results
    
    async def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        return self.doc_store.get(doc_id)
    
    async def get_document_count(self) -> int:
        return len(self.doc_store)
    
    async def clear(self):
        self.index = faiss.IndexFlatIP(self.dimension)
        self.doc_store.clear()
        self.id_to_idx.clear()
        self.idx_to_id.clear()
        self.next_idx = 0
        self._save_index()


vector_store: Optional[VectorStore] = None


async def get_vector_store() -> VectorStore:
    global vector_store
    if vector_store is None:
        vector_store = VectorStore()
        await vector_store.initialize()
    return vector_store
