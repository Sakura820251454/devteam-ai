"""
记忆高级服务 - Phase 4.3+ 深度优化

提供：
- 记忆相关性衰减
- 记忆去重与合并
- 动态相关性更新
- 记忆溯源
- 安全隐私标记
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import re

from app.models.memory_db import MemoryLevel


@dataclass
class MemoryQuality:
    """记忆质量指标"""
    freshness_score: float = 1.0  # 新鲜度 (0-1)
    relevance_score: float = 1.0  # 相关性 (0-1)
    utility_score: float = 0.0  # 实用性 (0-1)
    overall_quality: float = 0.0  # 综合质量


@dataclass
class MemorySource:
    """记忆来源信息"""
    source_type: str  # conversation, task, system, import
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    creator_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
    confidence: float = 1.0


class MemoryDecayEngine:
    """
    记忆衰减引擎
    
    实现时间衰减模型：
    - 指数衰减
    - 阶梯衰减
    - 使用频率修正衰减
    """
    
    def __init__(
        self,
        halflife_days: int = 30,
        min_score: float = 0.1,
        use_bonus_multiplier: float = 2.0,
    ):
        self.halflife_days = halflife_days
        self.min_score = min_score
        self.use_bonus_multiplier = use_bonus_multiplier
    
    def calculate_decayed_score(
        self,
        initial_score: float,
        days_since_creation: float,
        usage_count: int = 0,
    ) -> float:
        """
        计算衰减后的相关性分数
        
        使用指数衰减 + 使用频率修正
        """
        if days_since_creation <= 0:
            return initial_score
        
        # 基础指数衰减
        decay_factor = 0.5 ** (days_since_creation / self.halflife_days)
        base_score = initial_score * decay_factor
        
        # 使用频率奖励
        usage_bonus = 1.0 + (usage_count / 10.0) * (self.use_bonus_multiplier - 1.0)
        usage_bonus = min(usage_bonus, self.use_bonus_multiplier)
        
        final_score = base_score * usage_bonus
        return max(final_score, self.min_score)
    
    def calculate_freshness(
        self,
        created_at: datetime,
        last_accessed_at: Optional[datetime] = None,
    ) -> float:
        """计算记忆新鲜度"""
        now = datetime.now()
        
        if last_accessed_at:
            days_since_access = (now - last_accessed_at).total_seconds() / (24 * 3600)
            freshness = max(0.0, 1.0 - days_since_access / 90.0)
        else:
            days_since_creation = (now - created_at).total_seconds() / (24 * 3600)
            freshness = max(0.0, 1.0 - days_since_creation / 90.0)
        
        return freshness


class MemoryDeduplicator:
    """
    记忆去重引擎
    
    检测重复或高度相似的记忆
    """
    
    def __init__(
        self,
        content_similarity_threshold: float = 0.85,
        tag_overlap_threshold: float = 0.7,
    ):
        self.content_threshold = content_similarity_threshold
        self.tag_threshold = tag_overlap_threshold
    
    def compute_content_hash(self, content: str) -> str:
        """计算内容哈希"""
        cleaned = re.sub(r'\s+', ' ', content.strip()).lower()
        return hashlib.md5(cleaned.encode('utf-8')).hexdigest()
    
    def compute_similarity(
        self,
        content1: str,
        content2: str,
        tags1: Optional[List[str]] = None,
        tags2: Optional[List[str]] = None,
    ) -> float:
        """计算两个记忆的相似度"""
        content_score = self._content_similarity(content1, content2)
        tag_score = self._tag_similarity(tags1 or [], tags2 or [])
        
        return (content_score * 0.7 + tag_score * 0.3)
    
    def _content_similarity(self, a: str, b: str) -> float:
        """简单的内容相似度（基于词袋）"""
        if not a or not b:
            return 0.0
        
        words_a = set(re.findall(r'\w+', a.lower()))
        words_b = set(re.findall(r'\w+', b.lower()))
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        return len(intersection) / len(union)
    
    def _tag_similarity(self, tags1: List[str], tags2: List[str]) -> float:
        """标签相似度"""
        if not tags1 or not tags2:
            return 0.0
        
        set1 = set(t.lower() for t in tags1)
        set2 = set(t.lower() for t in tags2)
        
        intersection = set1 & set2
        union = set1 | set2
        
        return len(intersection) / len(union) if union else 0.0
    
    def find_duplicates(
        self,
        memories: List[Dict],
    ) -> List[List[Dict]]:
        """找出重复的记忆组"""
        duplicates = []
        processed: Set[str] = set()
        
        for i, mem1 in enumerate(memories):
            if mem1["id"] in processed:
                continue
            
            group = [mem1]
            processed.add(mem1["id"])
            
            for j, mem2 in enumerate(memories):
                if i >= j or mem2["id"] in processed:
                    continue
                
                similarity = self.compute_similarity(
                    mem1["content"],
                    mem2["content"],
                    mem1.get("tags", []),
                    mem2.get("tags", []),
                )
                
                if similarity >= self.content_threshold:
                    group.append(mem2)
                    processed.add(mem2["id"])
            
            if len(group) > 1:
                duplicates.append(group)
        
        return duplicates
    
    def merge_memories(
        self,
        memories: List[Dict],
        strategy: str = "newest",
    ) -> Dict:
        """
        合并多个记忆
        
        策略：
        - newest: 保留最新的
        - combined: 组合内容
        """
        if not memories:
            raise ValueError("No memories to merge")
        
        if strategy == "newest":
            memories_sorted = sorted(
                memories,
                key=lambda m: m.get("created_at", datetime.now()),
                reverse=True
            )
            result = memories_sorted[0].copy()
        elif strategy == "combined":
            memories_sorted = sorted(
                memories,
                key=lambda m: m.get("usage_count", 0),
                reverse=True
            )
            main = memories_sorted[0].copy()
            
            combined_tags: Set[str] = set()
            for mem in memories:
                combined_tags.update(mem.get("tags", []))
            main["tags"] = list(combined_tags)
            
            main["usage_count"] = sum(m.get("usage_count", 0) for m in memories)
            result = main
        else:
            result = memories[0].copy()
        
        result["_merged_from"] = [m["id"] for m in memories]
        return result


class MemoryPrivacyEngine:
    """
    记忆隐私安全引擎
    
    敏感内容检测和标记
    """
    
    SENSITIVE_PATTERNS = [
        (r'(password|passwd|pwd)\s*[=:]\s*\S+', 'secret'),
        (r'(api[_-]?key|token|secret)\s*[=:]\s*\S+', 'credential'),
        (r'(\d{1,3}\.){3}\d{1,3}', 'ip_address'),
        (r'[\w\.-]+@[\w\.-]+', 'email'),
    ]
    
    def __init__(self):
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), label)
            for pattern, label in self.SENSITIVE_PATTERNS
        ]
    
    def detect_sensitive_content(
        self,
        content: str,
    ) -> List[Dict[str, str]]:
        """检测敏感内容"""
        detections = []
        for pattern, label in self.compiled_patterns:
            for match in pattern.finditer(content):
                detections.append({
                    "type": label,
                    "position": match.start(),
                    "length": len(match.group(0)),
                })
        return detections
    
    def mark_sensitive(
        self,
        memory_data: Dict,
    ) -> Dict:
        """标记敏感记忆"""
        content = memory_data.get("content", "")
        detections = self.detect_sensitive_content(content)
        
        if detections:
            memory_data["_sensitive"] = True
            memory_data["_sensitive_types"] = list({d["type"] for d in detections})
        
        return memory_data


class MemoryEnhancementService:
    """
    记忆增强综合服务
    
    整合所有记忆优化功能
    """
    
    def __init__(self):
        self.decay_engine = MemoryDecayEngine()
        self.deduplicator = MemoryDeduplicator()
        self.privacy_engine = MemoryPrivacyEngine()
    
    def enhance_memory(
        self,
        memory: Dict,
    ) -> Dict:
        """增强单个记忆"""
        result = memory.copy()
        
        # 标记敏感内容
        result = self.privacy_engine.mark_sensitive(result)
        
        # 计算质量分数
        quality = self.calculate_quality(memory)
        result["_quality"] = {
            "freshness": quality.freshness_score,
            "relevance": quality.relevance_score,
            "utility": quality.utility_score,
            "overall": quality.overall_quality,
        }
        
        return result
    
    def calculate_quality(
        self,
        memory: Dict,
    ) -> MemoryQuality:
        """计算记忆质量"""
        created_at = memory.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        last_accessed_at = memory.get("last_accessed_at")
        if isinstance(last_accessed_at, str):
            last_accessed_at = datetime.fromisoformat(last_accessed_at)
        
        usage_count = memory.get("usage_count", 0)
        relevance_score = memory.get("relevance_score", 1.0)
        
        # 计算各维度
        freshness = self.decay_engine.calculate_freshness(created_at, last_accessed_at)
        
        days_since_creation = (datetime.now() - created_at).total_seconds() / (24 * 3600)
        decayed_relevance = self.decay_engine.calculate_decayed_score(
            relevance_score, days_since_creation, usage_count
        )
        
        utility = min(1.0, usage_count / 20.0)
        
        overall = (
            freshness * 0.3 +
            decayed_relevance * 0.5 +
            utility * 0.2
        )
        
        return MemoryQuality(
            freshness_score=freshness,
            relevance_score=decayed_relevance,
            utility_score=utility,
            overall_quality=overall,
        )
    
    def refresh_memories(
        self,
        memories: List[Dict],
    ) -> List[Dict]:
        """刷新一批记忆的分数"""
        return [self.enhance_memory(m) for m in memories]


memory_enhancer = MemoryEnhancementService()
