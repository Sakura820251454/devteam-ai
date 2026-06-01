"""
记忆晋升服务 - Phase 4 优化

实现记忆层级的自动晋升机制：
- L1 Working → L2 Short-term
- L2 Short-term → L3 Long-term
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.models.memory_db import MemoryLevel


@dataclass
class PromotionRule:
    """晋升规则"""
    from_level: str
    to_level: str
    usage_threshold: int = 5
    days_threshold: int = 7
    relevance_threshold: float = 0.5


class MemoryPromotionService:
    """
    记忆晋升服务
    
    自动评估和晋升记忆层级：
    - 工作记忆 → 短期记忆: 频繁访问 + 一定时间
    - 短期记忆 → 长期记忆: 持续访问 + 高相关度
    """
    
    DEFAULT_RULES = [
        PromotionRule(
            from_level=MemoryLevel.WORKING,
            to_level=MemoryLevel.SHORT_TERM,
            usage_threshold=3,
            days_threshold=1,
            relevance_threshold=0.3,
        ),
        PromotionRule(
            from_level=MemoryLevel.SHORT_TERM,
            to_level=MemoryLevel.LONG_TERM,
            usage_threshold=10,
            days_threshold=30,
            relevance_threshold=0.6,
        ),
    ]
    
    def __init__(self, rules: Optional[List[PromotionRule]] = None):
        self.rules = rules or self.DEFAULT_RULES
    
    def evaluate_promotion(
        self,
        memory: Dict[str, Any],
    ) -> Optional[str]:
        """
        评估记忆是否应该晋升
        
        Args:
            memory: 记忆数据
            
        Returns:
            目标层级，如果不需要晋升则返回 None
        """
        current_level = memory.get("level", MemoryLevel.WORKING)
        usage_count = memory.get("usage_count", 0)
        relevance_score = memory.get("relevance_score", 1.0)
        created_at = memory.get("created_at")
        
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                created_at = datetime.now()
        elif created_at is None:
            created_at = datetime.now()
        
        days_elapsed = (datetime.now() - created_at).days
        
        for rule in self.rules:
            if rule.from_level != current_level:
                continue
            
            usage_ok = usage_count >= rule.usage_threshold
            time_ok = days_elapsed >= rule.days_threshold
            relevance_ok = relevance_score >= rule.relevance_threshold
            
            if usage_ok and time_ok and relevance_ok:
                return rule.to_level
        
        return None
    
    def get_promotion_candidates(
        self,
        memories: List[Dict[str, Any]],
        level: Optional[str] = None,
    ) -> List[tuple[Dict[str, Any], str]]:
        """
        获取所有应该晋升的记忆
        
        Returns:
            [(memory, target_level), ...]
        """
        candidates = []
        
        for memory in memories:
            if level and memory.get("level") != level:
                continue
            
            target_level = self.evaluate_promotion(memory)
            if target_level:
                candidates.append((memory, target_level))
        
        candidates.sort(
            key=lambda x: (
                x[1],  # 先按目标层级
                -x[0].get("usage_count", 0),  # 再按使用次数
            )
        )
        
        return candidates

    def manual_promote(
        self,
        memories: List[Dict[str, Any]],
        memory_ids: List[str],
        target_level: str,
    ) -> List[tuple[Dict[str, Any], str]]:
        """
        手动晋升 — 统筹 Agent 在复盘时调用

        跳过自动规则检查，直接晋升指定记忆到目标层级。

        Args:
            memories: 所有记忆数据列表
            memory_ids: 要晋升的记忆 ID 列表
            target_level: 目标层级

        Returns:
            [(memory, target_level), ...] 验证通过的记忆列表
        """
        # 合法的晋升路径
        valid_targets = {
            MemoryLevel.WORKING: [MemoryLevel.SHORT_TERM, MemoryLevel.LONG_TERM],
            MemoryLevel.SHORT_TERM: [MemoryLevel.LONG_TERM],
        }

        # 验证目标层级是否已知
        known_levels = {MemoryLevel.WORKING, MemoryLevel.SHORT_TERM, MemoryLevel.LONG_TERM}
        if target_level not in known_levels:
            return []

        id_set = set(memory_ids)
        results = []

        for memory in memories:
            if memory.get("id") not in id_set:
                continue

            current_level = memory.get("level", MemoryLevel.WORKING)
            allowed = valid_targets.get(current_level, [])
            if target_level in allowed or target_level == current_level:
                results.append((memory, target_level))

        return results

    def should_archive(
        self,
        memory: Dict[str, Any],
        archive_after_days: int = 365,
    ) -> bool:
        """
        判断记忆是否应该归档
        
        长期记忆如果在一定天数内没有被访问，则归档
        """
        level = memory.get("level")
        if level != MemoryLevel.LONG_TERM:
            return False
        
        last_accessed = memory.get("last_accessed_at")
        if isinstance(last_accessed, str):
            try:
                last_accessed = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
            except ValueError:
                last_accessed = datetime.now()
        elif last_accessed is None:
            last_accessed = datetime.now()
        
        days_since_access = (datetime.now() - last_accessed).days
        return days_since_access >= archive_after_days
    
    def get_statistics(
        self,
        memories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """获取记忆层级统计"""
        stats = {
            "total": len(memories),
            "by_level": {
                MemoryLevel.WORKING: 0,
                MemoryLevel.SHORT_TERM: 0,
                MemoryLevel.LONG_TERM: 0,
            },
            "promotion_candidates": {
                MemoryLevel.WORKING: 0,
                MemoryLevel.SHORT_TERM: 0,
            },
            "avg_usage": {},
            "avg_relevance": {},
        }
        
        level_memories = {level: [] for level in stats["by_level"]}
        
        for memory in memories:
            level = memory.get("level", MemoryLevel.WORKING)
            if level in level_memories:
                level_memories[level].append(memory)
                stats["by_level"][level] += 1
            
            target = self.evaluate_promotion(memory)
            if target:
                if target not in stats["promotion_candidates"]:
                    stats["promotion_candidates"][target] = 0
                stats["promotion_candidates"][target] += 1
        
        for level, level_list in level_memories.items():
            if level_list:
                total_usage = sum(m.get("usage_count", 0) for m in level_list)
                total_relevance = sum(m.get("relevance_score", 0) for m in level_list)
                count = len(level_list)
                
                stats["avg_usage"][level] = total_usage / count
                stats["avg_relevance"][level] = total_relevance / count
            else:
                stats["avg_usage"][level] = 0
                stats["avg_relevance"][level] = 0
        
        return stats


promotion_service = MemoryPromotionService()
