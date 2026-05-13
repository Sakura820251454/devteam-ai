"""
上下文压缩服务 - Phase 4.6

提供多种压缩策略：
1. 摘要压缩 - 使用 LLM 生成摘要
2. 重要性压缩 - 保留重要消息
3. Token限制压缩 - 按token数量限制
4. 智能合并 - 合并相邻相似消息
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

from app.models.agent_context import MemoryEntry


class CompressionStrategy(str, Enum):
    """压缩策略"""
    AUTO = "auto"                    # 自动选择最佳策略
    SUMMARY = "summary"              # 生成摘要
    IMPORTANCE = "importance"        # 基于重要性过滤
    TOKEN_LIMIT = "token_limit"      # 按token限制
    MERGE_ADJACENT = "merge_adjacent" # 合并相邻消息
    TRUNCATE = "truncate"            # 简单截断


@dataclass
class CompressionConfig:
    """压缩配置"""
    strategy: CompressionStrategy = CompressionStrategy.AUTO
    
    # Token限制
    max_tokens: int = 4096
    min_tokens: int = 1024
    
    # 重要性阈值
    importance_threshold: float = 0.3
    
    # 合并配置
    merge_similarity_threshold: float = 0.8
    max_merge_distance: int = 3  # 最大间隔消息数
    
    # 摘要配置
    summary_ratio: float = 0.3  # 摘要长度占原长比例
    
    # 保留配置
    preserve_system_prompt: bool = True
    preserve_last_n_messages: int = 3


@dataclass
class CompressionResult:
    """压缩结果"""
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategy: CompressionStrategy
    messages_removed: int
    messages_merged: int
    summary_text: Optional[str] = None
    compressed_messages: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MessageImportance:
    """消息重要性评估"""
    message_id: str
    importance_score: float
    reason: str
    factors: Dict[str, float] = field(default_factory=dict)


class ContextCompressor:
    """
    上下文压缩器
    
    提供多种策略压缩对话上下文，节省token使用
    """
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
    
    async def compress(
        self,
        messages: List[Dict[str, Any]],
        strategy: Optional[CompressionStrategy] = None,
        max_tokens: Optional[int] = None,
    ) -> CompressionResult:
        """
        压缩上下文消息
        
        Args:
            messages: 消息列表
            strategy: 压缩策略（可选，默认使用配置）
            max_tokens: 最大token数（可选，覆盖配置）
            
        Returns:
            压缩结果
        """
        if not messages:
            return CompressionResult(
                original_tokens=0,
                compressed_tokens=0,
                compression_ratio=0.0,
                strategy=strategy or self.config.strategy,
                messages_removed=0,
                messages_merged=0,
                compressed_messages=[],
            )
        
        strategy = strategy or self.config.strategy
        max_tokens = max_tokens or self.config.max_tokens
        
        original_tokens = self._estimate_tokens(messages)
        
        if original_tokens <= max_tokens:
            return CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                strategy=strategy,
                messages_removed=0,
                messages_merged=0,
                compressed_messages=messages.copy(),
            )
        
        if strategy == CompressionStrategy.AUTO:
            return await self._auto_compress(messages, max_tokens)
        
        if strategy == CompressionStrategy.SUMMARY:
            return await self._summary_compress(messages, max_tokens)
        
        if strategy == CompressionStrategy.IMPORTANCE:
            return await self._importance_compress(messages, max_tokens)
        
        if strategy == CompressionStrategy.TOKEN_LIMIT:
            return await self._token_limit_compress(messages, max_tokens)
        
        if strategy == CompressionStrategy.MERGE_ADJACENT:
            return await self._merge_adjacent_compress(messages, max_tokens)
        
        if strategy == CompressionStrategy.TRUNCATE:
            return await self._truncate_compress(messages, max_tokens)
        
        return await self._auto_compress(messages, max_tokens)
    
    async def _auto_compress(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
    ) -> CompressionResult:
        """自动选择最佳压缩策略"""
        original_tokens = self._estimate_tokens(messages)
        target_ratio = max_tokens / original_tokens
        
        if target_ratio > 0.7:
            return await self._merge_adjacent_compress(messages, max_tokens)
        elif target_ratio > 0.4:
            return await self._importance_compress(messages, max_tokens)
        else:
            return await self._summary_compress(messages, max_tokens)
    
    async def _summary_compress(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
    ) -> CompressionResult:
        """基于摘要的压缩"""
        original_tokens = self._estimate_tokens(messages)
        
        system_messages = [m for m in messages if m.get("role") == "system"]
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        if len(user_messages) + len(assistant_messages) < 2:
            return await self._token_limit_compress(messages, max_tokens)
        
        conversation_text = "\n".join([
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages
            if m.get("role") in ["user", "assistant"]
        ])
        
        summary_text = self._generate_summary(conversation_text)
        summary_tokens = self._estimate_tokens([{"content": summary_text}])
        
        system_content = "\n".join([m.get("content", "") for m in system_messages])
        
        compressed_messages = []
        if self.config.preserve_system_prompt and system_content:
            compressed_messages.append({"role": "system", "content": system_content})
        
        compressed_messages.append({
            "role": "system",
            "content": f"对话摘要：{summary_text}",
        })
        
        compressed_messages.extend(
            messages[-self.config.preserve_last_n_messages:]
        )
        
        compressed_tokens = self._estimate_tokens(compressed_messages)
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens,
            strategy=CompressionStrategy.SUMMARY,
            messages_removed=len(messages) - len(compressed_messages),
            messages_merged=0,
            summary_text=summary_text,
            compressed_messages=compressed_messages,
        )
    
    def _generate_summary(self, text: str) -> str:
        """生成摘要（简化实现，Phase 5升级为LLM）"""
        sentences = text.split("。")
        if len(sentences) <= 3:
            return text[:500]
        
        key_points = []
        for i, sentence in enumerate(sentences[:10]):
            if i == 0:
                key_points.append(sentence)
            elif len(sentence) > 10:
                key_points.append(sentence)
        
        summary = "。".join(key_points[:3]) + "。"
        return summary[:300]
    
    async def _importance_compress(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
    ) -> CompressionResult:
        """基于重要性的压缩"""
        original_tokens = self._estimate_tokens(messages)
        
        importance_list = []
        for i, message in enumerate(messages):
            importance = self._calculate_importance(message, i, messages)
            importance_list.append((importance, message))
        
        importance_list.sort(
            key=lambda x: x[0].importance_score,
            reverse=True
        )
        
        compressed_messages = []
        current_tokens = 0
        
        for importance, message in importance_list:
            message_tokens = self._estimate_tokens([message])
            
            if current_tokens + message_tokens <= max_tokens:
                compressed_messages.append(message)
                current_tokens += message_tokens
            else:
                break
        
        compressed_messages.sort(
            key=lambda m: messages.index(m)
        )
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=current_tokens,
            compression_ratio=current_tokens / original_tokens,
            strategy=CompressionStrategy.IMPORTANCE,
            messages_removed=len(messages) - len(compressed_messages),
            messages_merged=0,
            compressed_messages=compressed_messages,
        )
    
    def _calculate_importance(
        self,
        message: Dict[str, Any],
        index: int,
        all_messages: List[Dict[str, Any]],
    ) -> MessageImportance:
        """计算消息重要性"""
        factors = {}
        score = 0.0
        
        role = message.get("role", "user")
        content = message.get("content", "")
        
        factors["recency"] = max(0.1, (len(all_messages) - index) / len(all_messages))
        score += factors["recency"] * 0.3
        
        if role == "system":
            factors["system_role"] = 1.0
            score += 0.4
        elif role == "user":
            factors["user_role"] = 0.7
            score += 0.2
        else:
            factors["assistant_role"] = 0.5
            score += 0.1
        
        content_length = len(content)
        if content_length > 500:
            factors["length"] = 0.8
            score += 0.15
        elif content_length < 20:
            factors["length"] = 0.3
            score += 0.05
        else:
            factors["length"] = 0.5
            score += 0.1
        
        keywords = ["需要", "必须", "重要", "紧急", "注意", "记住", "关键"]
        has_keyword = any(kw in content for kw in keywords)
        if has_keyword:
            factors["keywords"] = 1.0
            score += 0.15
        
        reason = "综合评估"
        if score > 0.7:
            reason = "重要消息"
        elif score < 0.3:
            reason = "次要消息"
        
        return MessageImportance(
            message_id=f"msg_{index}",
            importance_score=min(1.0, score),
            reason=reason,
            factors=factors,
        )
    
    async def _token_limit_compress(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
    ) -> CompressionResult:
        """基于token限制的压缩"""
        original_tokens = self._estimate_tokens(messages)
        
        compressed_messages = []
        current_tokens = 0
        
        for message in reversed(messages):
            message_tokens = self._estimate_tokens([message])
            
            if current_tokens + message_tokens <= max_tokens:
                compressed_messages.insert(0, message)
                current_tokens += message_tokens
            else:
                if compressed_messages:
                    first_message = compressed_messages[0]
                    remaining = max_tokens - current_tokens
                    if remaining > 0 and message_tokens > remaining:
                        truncated = self._truncate_message(message, remaining)
                        compressed_messages.insert(0, truncated)
                        current_tokens += remaining
                break
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=current_tokens,
            compression_ratio=current_tokens / original_tokens,
            strategy=CompressionStrategy.TOKEN_LIMIT,
            messages_removed=len(messages) - len(compressed_messages),
            messages_merged=0,
            compressed_messages=compressed_messages,
        )
    
    def _truncate_message(self, message: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
        """截断消息到指定token数"""
        content = message.get("content", "")
        max_chars = max_tokens * 4
        
        if len(content) <= max_chars:
            return message
        
        truncated = content[:max_chars - 3] + "..."
        return {**message, "content": truncated, "_truncated": True}
    
    async def _merge_adjacent_compress(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
    ) -> CompressionResult:
        """合并相邻相似消息"""
        original_tokens = self._estimate_tokens(messages)
        
        merged = []
        i = 0
        
        while i < len(messages):
            current = messages[i]
            
            if i + 1 < len(messages):
                next_msg = messages[i + 1]
                
                similarity = self._message_similarity(current, next_msg)
                
                if (
                    similarity >= self.config.merge_similarity_threshold and
                    current.get("role") == next_msg.get("role")
                ):
                    merged_message = {
                        "role": current["role"],
                        "content": current.get("content", "") + "\n" + next_msg.get("content", ""),
                        "_merged": True,
                        "_merged_count": 2,
                    }
                    merged.append(merged_message)
                    i += 2
                    continue
            
            merged.append(current)
            i += 1
        
        if self._estimate_tokens(merged) > max_tokens:
            return await self._token_limit_compress(merged, max_tokens)
        
        merged_count = len(messages) - len(merged)
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=self._estimate_tokens(merged),
            compression_ratio=self._estimate_tokens(merged) / original_tokens,
            strategy=CompressionStrategy.MERGE_ADJACENT,
            messages_removed=0,
            messages_merged=merged_count,
            compressed_messages=merged,
        )
    
    def _message_similarity(self, msg1: Dict, msg2: Dict) -> float:
        """计算消息相似度"""
        content1 = msg1.get("content", "").lower()
        content2 = msg2.get("content", "").lower()
        
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    async def _truncate_compress(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
    ) -> CompressionResult:
        """简单截断压缩"""
        original_tokens = self._estimate_tokens(messages)
        
        preserved = messages[-self.config.preserve_last_n_messages:]
        
        preserved_tokens = self._estimate_tokens(preserved)
        remaining_tokens = max_tokens - preserved_tokens
        
        if remaining_tokens <= 0:
            return CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=preserved_tokens,
                compression_ratio=preserved_tokens / original_tokens,
                strategy=CompressionStrategy.TRUNCATE,
                messages_removed=len(messages) - len(preserved),
                messages_merged=0,
                compressed_messages=preserved,
            )
        
        previous_messages = messages[:-self.config.preserve_last_n_messages]
        previous_tokens = self._estimate_tokens(previous_messages)
        
        if previous_tokens <= remaining_tokens:
            compressed_messages = messages
        else:
            compressed_messages = previous_messages[-int(len(previous_messages) * remaining_tokens / previous_tokens):] + preserved
        
        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=self._estimate_tokens(compressed_messages),
            compression_ratio=self._estimate_tokens(compressed_messages) / original_tokens,
            strategy=CompressionStrategy.TRUNCATE,
            messages_removed=len(messages) - len(compressed_messages),
            messages_merged=0,
            compressed_messages=compressed_messages,
        )
    
    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """估算token数量"""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return int(total_chars / 4)


class MemoryCompressor:
    """
    记忆压缩器
    
    压缩记忆条目，节省存储和检索开销
    """
    
    def __init__(self):
        self.context_compressor = ContextCompressor()
    
    async def compress_memories(
        self,
        memories: List[MemoryEntry],
        max_tokens: int = 4096,
    ) -> CompressionResult:
        """
        压缩记忆列表
        
        Args:
            memories: 记忆条目列表
            max_tokens: 最大token数
            
        Returns:
            压缩结果
        """
        messages = [
            {
                "role": "user" if "user" in m.tags else "assistant",
                "content": m.content,
                "memory_id": m.id,
            }
            for m in memories
        ]
        
        return await self.context_compressor.compress(
            messages,
            max_tokens=max_tokens,
        )


context_compressor = ContextCompressor()
memory_compressor = MemoryCompressor()
