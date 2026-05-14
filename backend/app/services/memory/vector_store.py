"""
向量存储服务 - Phase 4.2

使用 FAISS 进行向量检索，支持语义相似度搜索
"""
import os
import json
import pickle
import math
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

# 降级导入：缺失的依赖提供纯 Python 替代方案
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False
    np = None  # type: ignore

try:
    import faiss
    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False
    faiss = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False
    SentenceTransformer = None  # type: ignore


@dataclass
class VectorDocument:
    id: str
    content: str
    embedding: Any = None  # np.ndarray or List[float] depending on backend
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

        self.embedder: Any = None
        self.index: Any = None
        self.doc_store: Dict[str, VectorDocument] = {}
        self.id_to_idx: Dict[str, int] = {}
        self.idx_to_id: Dict[int, str] = {}
        self.next_idx: int = 0

        self._use_faiss = _HAS_FAISS and _HAS_NUMPY
        self._use_transformers = _HAS_SENTENCE_TRANSFORMERS

        # 降级模式：使用纯 Python 实现
        self._fallback_embeddings: Dict[str, List[float]] = {}

        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return

        os.makedirs(self.index_path, exist_ok=True)

        if self._use_transformers and SentenceTransformer:
            self.embedder = SentenceTransformer(self.embedding_model_name)
            actual_dim = self.embedder.get_sentence_embedding_dimension()
            if actual_dim != self.dimension:
                self.dimension = actual_dim

        if self._use_faiss:
            self.index = faiss.IndexFlatIP(self.dimension)
        else:
            # 纯 Python 降级：使用 dict 存储向量
            self._fallback_embeddings = {}

        self._load_index()
        self._initialized = True

    def _compute_tf_idf_embedding(self, text: str) -> List[float]:
        """简易 TF-IDF 向量化（降级方案）"""
        # 使用字符级 n-gram (1-3) 作为特征
        features: Dict[str, float] = {}
        text_lower = text.lower()

        # 字符 n-grams
        for n in range(1, 4):
            for i in range(len(text_lower) - n + 1):
                ngram = text_lower[i:i + n]
                features[ngram] = features.get(ngram, 0) + 1

        # 归一化
        total = sum(features.values()) or 1
        vector = [features.get(k, 0) / total for k in sorted(features.keys())]

        # 填充或截断到指定维度
        if len(vector) < self.dimension:
            vector.extend([0.0] * (self.dimension - len(vector)))
        else:
            vector = vector[:self.dimension]

        return vector

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """纯 Python 余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _get_embedding(self, text: str) -> Any:
        if self._use_transformers and self.embedder:
            embedding = self.embedder.encode(text, normalize_embeddings=True)
            if self._use_faiss:
                return embedding.astype(np.float32)
            return embedding.tolist()
        else:
            return self._compute_tf_idf_embedding(text)

    def _load_index(self):
        meta_file = os.path.join(self.index_path, "metadata.json")

        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 恢复 doc_store
                    for doc_data in data.get("documents", []):
                        doc = VectorDocument(
                            id=doc_data["id"],
                            content=doc_data["content"],
                            embedding=doc_data.get("embedding"),
                            metadata=doc_data.get("metadata", {})
                        )
                        self.doc_store[doc.id] = doc

                    self.id_to_idx = {k: int(v) for k, v in data.get("id_to_idx", {}).items()}
                    self.idx_to_id = {int(k): v for k, v in data.get("idx_to_id", {}).items()}
                    self.next_idx = data.get("next_idx", 0)

                    if self._use_faiss:
                        self._rebuild_faiss_index()
            except Exception:
                if self._use_faiss:
                    self.index = faiss.IndexFlatIP(self.dimension)

    def _save_index(self):
        meta_file = os.path.join(self.index_path, "metadata.json")

        documents_data = []
        for doc in self.doc_store.values():
            doc_data = {
                "id": doc.id,
                "content": doc.content,
                "embedding": doc.embedding.tolist() if self._use_faiss and hasattr(doc.embedding, 'tolist') else doc.embedding,
                "metadata": doc.metadata
            }
            documents_data.append(doc_data)

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "documents": documents_data,
                "id_to_idx": {k: v for k, v in self.id_to_idx.items()},
                "idx_to_id": {str(k): v for k, v in self.idx_to_id.items()},
                "next_idx": self.next_idx
            }, f, ensure_ascii=False)

    def _rebuild_faiss_index(self):
        """从 doc_store 重建 FAISS 索引"""
        if not self._use_faiss:
            return
        self.index = faiss.IndexFlatIP(self.dimension)
        for doc_id in sorted(self.id_to_idx, key=lambda k: self.id_to_idx[k]):
            doc = self.doc_store.get(doc_id)
            if doc and doc.embedding is not None:
                emb = doc.embedding
                if hasattr(emb, 'tolist'):
                    emb_arr = np.array([emb])
                else:
                    emb_arr = np.array([emb], dtype=np.float32)
                self.index.add(emb_arr)

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

        if self._use_faiss:
            if hasattr(embedding, 'tolist'):
                self.index.add(np.array([embedding]))
            else:
                self.index.add(np.array([embedding], dtype=np.float32))
        else:
            self._fallback_embeddings[doc_id] = embedding if isinstance(embedding, list) else embedding.tolist()

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

        embedding = self._get_embedding(content)

        doc = VectorDocument(
            id=doc_id,
            content=content,
            embedding=embedding,
            metadata=metadata or self.doc_store[doc_id].metadata
        )

        self.doc_store[doc_id] = doc

        if self._use_faiss:
            self._rebuild_faiss_index()
        else:
            self._fallback_embeddings[doc_id] = embedding if isinstance(embedding, list) else embedding.tolist()

        self._save_index()
        return True

    async def delete_document(self, doc_id: str) -> bool:
        if doc_id not in self.doc_store:
            return False

        del self.doc_store[doc_id]
        if doc_id in self.id_to_idx:
            del self.id_to_idx[doc_id]
        self._fallback_embeddings.pop(doc_id, None)

        if self._use_faiss:
            self._rebuild_faiss_index()

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

        if len(self.doc_store) == 0:
            return []

        query_embedding = self._get_embedding(query)

        if self._use_faiss:
            if self.index.ntotal == 0:
                return []

            search_k = min(k * 3, self.index.ntotal)
            if hasattr(query_embedding, 'tolist'):
                q_emb = np.array([query_embedding])
            else:
                q_emb = np.array([query_embedding], dtype=np.float32)
            distances, indices = self.index.search(q_emb, search_k)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:
                    continue
                doc_id = self.idx_to_id.get(int(idx))
                if not doc_id or doc_id not in self.doc_store:
                    continue
                doc = self.doc_store[doc_id]
                if filter_metadata:
                    if not all(doc.metadata.get(key) == value for key, value in filter_metadata.items()):
                        continue
                results.append((doc_id, float(dist), doc.metadata))
                if len(results) >= k:
                    break
        else:
            # 纯 Python 暴力搜索
            q_emb = query_embedding if isinstance(query_embedding, list) else query_embedding.tolist()
            scores = []
            for doc_id, doc in self.doc_store.items():
                if filter_metadata:
                    if not all(doc.metadata.get(key) == value for key, value in filter_metadata.items()):
                        continue
                doc_emb = self._fallback_embeddings.get(doc_id)
                if doc_emb is None:
                    continue
                score = self._cosine_similarity(q_emb, doc_emb)
                scores.append((doc_id, score, doc.metadata))

            scores.sort(key=lambda x: x[1], reverse=True)
            results = scores[:k]

        return results

    async def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        return self.doc_store.get(doc_id)

    async def get_document_count(self) -> int:
        return len(self.doc_store)

    async def clear(self):
        if self._use_faiss:
            self.index = faiss.IndexFlatIP(self.dimension)
        self._fallback_embeddings.clear()
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
