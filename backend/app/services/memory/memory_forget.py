"""
记忆遗忘服务 - Phase 4.5

智能遗忘机制：
1. 基于质量的遗忘（低质量记忆自动清理）
2. 基于时间的遗忘（长期未访问自动清理）
3. 基于容量的遗忘（超过容量限制时清理）
4. 手动清理
5. 定时自动清理
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.models.memory_db import MemoryLevel

logger = logging.getLogger(__name__)


class ForgetReason(str, Enum):
    """遗忘原因"""
    LOW_QUALITY = "low_quality"           # 质量太低
    TIME_EXPIRED = "time_expired"         # 时间过期
    NOT_ACCESSED = "not_accessed"         # 长期未访问
    CAPACITY_LIMIT = "capacity_limit"     # 容量限制
    MANUAL = "manual"                      # 手动清理
    DUPLICATE = "duplicate"               # 重复记忆


@dataclass
class ForgetPolicy:
    """遗忘策略配置"""
    # 质量阈值
    min_quality_threshold: float = 0.2
    
    # 时间阈值
    max_age_days: int = 365                # 超过365天自动遗忘
    not_accessed_days: int = 90            # 90天未访问自动遗忘
    
    # 容量限制
    max_memories_per_level: int = 100      # 每层最大记忆数
    max_total_memories: int = 500          # 总记忆数上限
    
    # 自动清理
    auto_forget_enabled: bool = True       # 是否启用自动遗忘
    auto_forget_interval_hours: int = 24   # 自动清理间隔（小时）
    
    # 保留策略
    preserve_important: bool = True       # 重要记忆不遗忘
    preserve_recent: bool = True           # 最近记忆不遗忘
    recent_days: int = 7                   # 最近7天不遗忘


@dataclass
class ForgetCandidate:
    """可遗忘记忆候选"""
    memory_id: str
    reason: ForgetReason
    priority: int  # 优先级，越高越先被遗忘
    quality_score: float = 0.0
    days_since_access: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryForgetService:
    """
    记忆遗忘服务
    
    核心功能：
    1. 评估哪些记忆应该被遗忘
    2. 执行遗忘操作
    3. 支持多种遗忘策略
    4. 自动定时清理
    """
    
    def __init__(self, policy: Optional[ForgetPolicy] = None):
        self.policy = policy or ForgetPolicy()
    
    def evaluate_forget_candidates(
        self,
        memories: List[Dict[str, Any]],
        agent_id: str,
    ) -> List[ForgetCandidate]:
        """
        评估哪些记忆应该被遗忘
        
        Args:
            memories: 记忆列表
            agent_id: Agent ID
            
        Returns:
            按优先级排序的遗忘候选列表
        """
        candidates = []
        
        for memory in memories:
            candidate = self._evaluate_single_memory(memory)
            if candidate:
                candidates.append(candidate)
        
        candidates.sort(key=lambda x: x.priority, reverse=True)
        return candidates
    
    def _evaluate_single_memory(
        self,
        memory: Dict[str, Any],
    ) -> Optional[ForgetCandidate]:
        """评估单个记忆"""
        memory_id = memory.get("id")
        level = memory.get("level", MemoryLevel.WORKING)
        relevance_score = memory.get("relevance_score", 1.0)
        usage_count = memory.get("usage_count", 0)
        created_at = memory.get("created_at")
        last_accessed = memory.get("last_accessed_at")
        
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                created_at = datetime.now()
        elif created_at is None:
            created_at = datetime.now()
        
        if isinstance(last_accessed, str):
            try:
                last_accessed = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
            except ValueError:
                last_accessed = created_at
        elif last_accessed is None:
            last_accessed = created_at
        
        now = datetime.now()
        days_since_creation = (now - created_at).total_seconds() / (24 * 3600)
        days_since_access = (now - last_accessed).total_seconds() / (24 * 3600)
        
        # 计算综合质量分数
        quality_score = self._calculate_quality(
            relevance_score=relevance_score,
            usage_count=usage_count,
            days_since_creation=days_since_creation,
            days_since_access=days_since_access,
        )
        
        priority = 0
        reason = None
        
        # 1. 检查是否保留
        if self._should_preserve(memory, days_since_access):
            return None
        
        # 2. 质量太低
        if quality_score < self.policy.min_quality_threshold:
            priority = 100 + int((self.policy.min_quality_threshold - quality_score) * 100)
            reason = ForgetReason.LOW_QUALITY
        
        # 3. 时间过期
        elif days_since_creation > self.policy.max_age_days:
            priority = 90 + min(int(days_since_creation - self.policy.max_age_days), 10)
            reason = ForgetReason.TIME_EXPIRED
        
        # 4. 长期未访问
        elif days_since_access > self.policy.not_accessed_days:
            priority = 80 + min(int(days_since_access - self.policy.not_accessed_days), 20)
            reason = ForgetReason.NOT_ACCESSED
        
        if reason:
            return ForgetCandidate(
                memory_id=memory_id,
                reason=reason,
                priority=priority,
                quality_score=quality_score,
                days_since_access=days_since_access,
                metadata={
                    "level": level,
                    "days_since_creation": days_since_creation,
                    "usage_count": usage_count,
                }
            )
        
        return None
    
    def _calculate_quality(
        self,
        relevance_score: float,
        usage_count: int,
        days_since_creation: float,
        days_since_access: float,
    ) -> float:
        """计算综合质量分数"""
        freshness_weight = 0.3
        relevance_weight = 0.5
        utility_weight = 0.2
        
        freshness = max(0, 1 - days_since_access / 90)
        
        relevance_decay = relevance_score * (0.5 ** (days_since_creation / 180))
        
        utility = min(1, usage_count / 20)
        
        quality = (
            freshness * freshness_weight +
            relevance_decay * relevance_weight +
            utility * utility_weight
        )
        
        return quality
    
    def _should_preserve(
        self,
        memory: Dict[str, Any],
        days_since_access: float,
    ) -> bool:
        """判断是否应该保留"""
        metadata = memory.get("metadata", {})
        
        if self.policy.preserve_important and metadata.get("important", False):
            return True
        
        if self.policy.preserve_recent and days_since_access < self.policy.recent_days:
            return True
        
        tags = memory.get("tags", [])
        if "important" in [t.lower() for t in tags]:
            return True
        
        return False
    
    def get_forget_plan(
        self,
        memories: List[Dict[str, Any]],
        agent_id: str,
        target_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        制定遗忘计划
        
        Args:
            memories: 记忆列表
            agent_id: Agent ID
            target_count: 目标保留数量
            
        Returns:
            遗忘计划
        """
        candidates = self.evaluate_forget_candidates(memories, agent_id)
        
        plan = {
            "total_memories": len(memories),
            "candidate_count": len(candidates),
            "candidates": [],
            "forget_count": 0,
            "by_reason": {},
        }
        
        if target_count:
            candidates_to_forget = candidates[target_count:]
        else:
            candidates_to_forget = candidates
        
        for candidate in candidates_to_forget:
            plan["candidates"].append({
                "memory_id": candidate.memory_id,
                "reason": candidate.reason.value,
                "priority": candidate.priority,
                "quality_score": candidate.quality_score,
            })
            
            reason_key = candidate.reason.value
            if reason_key not in plan["by_reason"]:
                plan["by_reason"][reason_key] = 0
            plan["by_reason"][reason_key] += 1
        
        plan["forget_count"] = len(candidates_to_forget)
        
        return plan
    
    def select_memories_to_forget(
        self,
        memories: List[Dict[str, Any]],
        agent_id: str,
        level: Optional[str] = None,
        max_forget: int = 50,
    ) -> List[str]:
        """
        选择要遗忘的记忆
        
        Returns:
            要遗忘的记忆ID列表
        """
        candidates = self.evaluate_forget_candidates(memories, agent_id)
        
        memory_ids = []
        for candidate in candidates:
            if level and candidate.metadata.get("level") != level:
                continue
            
            if len(memory_ids) >= max_forget:
                break
            
            memory_ids.append(candidate.memory_id)
        
        return memory_ids


class CapacityManager:
    """
    容量管理器
    
    确保记忆不会无限增长
    """
    
    def __init__(
        self,
        max_per_level: int = 100,
        max_total: int = 500,
    ):
        self.max_per_level = max_per_level
        self.max_total = max_total
    
    def check_capacity(
        self,
        memories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """检查容量状态"""
        total = len(memories)
        
        by_level = {
            MemoryLevel.WORKING: 0,
            MemoryLevel.SHORT_TERM: 0,
            MemoryLevel.LONG_TERM: 0,
        }
        
        for mem in memories:
            level = mem.get("level", MemoryLevel.WORKING)
            if level in by_level:
                by_level[level] += 1
        
        return {
            "total": total,
            "total_exceeded": total > self.max_total,
            "by_level": by_level,
            "level_exceeded": {
                level: count > self.max_per_level
                for level, count in by_level.items()
            },
        }
    
    def get_memories_to_remove(
        self,
        memories: List[Dict[str, Any]],
    ) -> List[str]:
        """
        获取需要移除的记忆
        
        优先级：
        1. 长期记忆 > 短期记忆 > 工作记忆
        2. 低质量 > 高质量
        3. 久未访问 > 最近访问
        """
        remove_ids = []
        
        capacity_status = self.check_capacity(memories)
        
        for level in [MemoryLevel.LONG_TERM, MemoryLevel.SHORT_TERM, MemoryLevel.WORKING]:
            level_count = capacity_status["by_level"].get(level, 0)
            level_excess = level_count - self.max_per_level
            
            if level_excess > 0:
                level_memories = [
                    m for m in memories
                    if m.get("level") == level
                ]
                
                sorted_memories = sorted(
                    level_memories,
                    key=lambda m: (
                        m.get("relevance_score", 1.0),
                        -(datetime.now() - m.get("last_accessed_at", datetime.now())).total_seconds()
                    )
                )
                
                to_remove = sorted_memories[:level_excess]
                remove_ids.extend([m["id"] for m in to_remove])
        
        total_excess = capacity_status["total"] - self.max_total
        if total_excess > 0 and len(remove_ids) < total_excess:
            remaining_excess = total_excess - len(remove_ids)
            
            for mem in memories:
                if mem["id"] in remove_ids:
                    continue
                if remaining_excess <= 0:
                    break
                remove_ids.append(mem["id"])
                remaining_excess -= 1
        
        return remove_ids


class IntelligentForgetScheduler:
    """
    智能遗忘调度器
    
    定时执行遗忘任务
    """
    
    def __init__(
        self,
        forget_service: MemoryForgetService,
        capacity_manager: CapacityManager,
    ):
        self.forget_service = forget_service
        self.capacity_manager = capacity_manager
        self._last_run: Optional[datetime] = None
    
    def should_run(self) -> bool:
        """检查是否应该执行遗忘"""
        if not self.forget_service.policy.auto_forget_enabled:
            return False
        
        if not self._last_run:
            return True
        
        hours_since_last = (
            datetime.now() - self._last_run
        ).total_seconds() / 3600
        
        return hours_since_last >= self.forget_service.policy.auto_forget_interval_hours
    
    async def run_forget_cycle(
        self,
        get_memories_func: Callable,  # async function to get memories
        delete_memory_func: Callable,  # async function to delete memory
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        执行一个遗忘周期
        
        Args:
            get_memories_func: 获取记忆的异步函数
            delete_memory_func: 删除记忆的异步函数
            agent_id: Agent ID
            
        Returns:
            执行结果
        """
        if not self.should_run():
            return {"status": "skipped", "reason": "not_due"}
        
        self._last_run = datetime.now()
        
        memories = await get_memories_func(agent_id)
        
        memories_data = [
            {
                "id": m.id,
                "level": m.level,
                "content": m.content,
                "relevance_score": m.relevance_score,
                "usage_count": m.usage_count,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "last_accessed_at": m.last_accessed_at.isoformat() if m.last_accessed_at else None,
                "metadata": m.extra_data or {},
                "tags": m.tags or [],
            }
            for m in memories
        ]
        
        quality_forget_ids = self.forget_service.select_memories_to_forget(
            memories_data, agent_id
        )
        
        capacity_status = self.capacity_manager.check_capacity(memories_data)
        capacity_forget_ids = self.capacity_manager.get_memories_to_remove(memories_data)
        
        all_forget_ids = list(set(quality_forget_ids + capacity_forget_ids))
        
        deleted_count = 0
        for mem_id in all_forget_ids:
            try:
                await delete_memory_func(mem_id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete memory {mem_id}: {e}")
        
        return {
            "status": "completed",
            "timestamp": self._last_run.isoformat(),
            "total_checked": len(memories_data),
            "quality_forgotten": len(quality_forget_ids),
            "capacity_forgotten": len(capacity_forget_ids),
            "total_forgotten": deleted_count,
        }


forget_service = MemoryForgetService()
capacity_manager = CapacityManager()
