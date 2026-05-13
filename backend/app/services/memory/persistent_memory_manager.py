from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.models.memory_db import (
    MemoryEntryModel,
    AgentContextModel,
    MemoryLevel
)
from app.models.agent_context import MemoryEntry as PydanticMemoryEntry
from app.services.memory.semantic_retriever import get_semantic_retriever
from app.services.memory.memory_promotion import promotion_service
from app.services.memory.memory_enhancement import memory_enhancer
from app.services.memory.memory_forget import forget_service, capacity_manager
from app.services.memory.memory_compressor import context_compressor, memory_compressor


class PersistentMemoryManager:
    """
    持久化记忆管理器
    
    参考 LangChain 的记忆管理接口，自研实现
    支持三层记忆的持久化存储和检索
    
    Phase 4.2 新增: 语义检索支持
    """
    
    def __init__(self, db: AsyncSession, use_semantic_search: bool = True):
        self.db = db
        self.use_semantic_search = use_semantic_search
    
    async def add_memory(
        self,
        agent_id: str,
        content: str,
        level: str = MemoryLevel.WORKING,
        tags: List[str] = None,
        source: str = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> PydanticMemoryEntry:
        """
        添加记忆到数据库
        
        Args:
            agent_id: Agent ID
            content: 记忆内容
            level: 记忆层级 (working/short_term/long_term)
            tags: 标签列表
            source: 来源 (如: "conversation", "task", "user")
            session_id: 会话 ID
            metadata: 元数据
            
        Returns:
            PydanticMemoryEntry: 创建的记忆条目
        """
        memory_id = f"mem_{agent_id}_{datetime.now().timestamp()}"
        
        entry = MemoryEntryModel(
            id=memory_id,
            agent_id=agent_id,
            session_id=session_id,
            content=content,
            level=level,
            tags=tags or [],
            source=source,
            extra_data=metadata or {},
            created_at=datetime.now(),
            last_accessed_at=datetime.now()
        )
        
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        
        if self.use_semantic_search:
            try:
                retriever = await get_semantic_retriever()
                await retriever.index_memory(
                    memory_id=memory_id,
                    content=content,
                    metadata={
                        "agent_id": agent_id,
                        "level": level,
                        "tags": tags or [],
                        "source": source,
                        "session_id": session_id
                    }
                )
            except Exception:
                pass
        
        return self._to_pydantic(entry)
    
    async def get_memory(
        self,
        memory_id: str
    ) -> Optional[PydanticMemoryEntry]:
        """根据 ID 获取记忆"""
        result = await self.db.execute(
            select(MemoryEntryModel).where(MemoryEntryModel.id == memory_id)
        )
        entry = result.scalar_one_or_none()
        
        if entry:
            entry.usage_count += 1
            entry.last_accessed_at = datetime.now()
            await self.db.commit()
            return self._to_pydantic(entry)
        
        return None
    
    async def get_agent_memories(
        self,
        agent_id: str,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PydanticMemoryEntry]:
        """
        获取 Agent 的所有记忆
        
        Args:
            agent_id: Agent ID
            level: 可选，按层级过滤
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            List[PydanticMemoryEntry]: 记忆列表
        """
        query = select(MemoryEntryModel).where(
            MemoryEntryModel.agent_id == agent_id
        )
        
        if level:
            query = query.where(MemoryEntryModel.level == level)
        
        query = query.order_by(MemoryEntryModel.last_accessed_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        return [self._to_pydantic(entry) for entry in entries]
    
    async def retrieve_memory(
        self,
        agent_id: str,
        query: str,
        level: Optional[str] = None,
        max_results: int = 10,
        use_semantic: bool = True
    ) -> List[PydanticMemoryEntry]:
        """
        检索相关记忆
        
        Phase 4.2 升级: 支持语义检索
        
        Args:
            agent_id: Agent ID
            query: 查询文本
            level: 可选，按层级过滤
            max_results: 最大返回数量
            use_semantic: 是否使用语义检索 (默认 True)
        """
        if self.use_semantic_search and use_semantic:
            return await self._semantic_retrieve(agent_id, query, level, max_results)
        else:
            return await self._keyword_retrieve(agent_id, query, level, max_results)
    
    async def _semantic_retrieve(
        self,
        agent_id: str,
        query: str,
        level: Optional[str],
        max_results: int
    ) -> List[PydanticMemoryEntry]:
        """语义检索 - 使用向量相似度"""
        query_stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.agent_id == agent_id
        )
        if level:
            query_stmt = query_stmt.where(MemoryEntryModel.level == level)
        
        result = await self.db.execute(query_stmt)
        all_entries = result.scalars().all()
        
        if not all_entries:
            return []
        
        memories_data = [
            {
                "id": entry.id,
                "content": entry.content,
                "level": entry.level,
                "tags": entry.tags or [],
                "relevance_score": entry.relevance_score or 1.0
            }
            for entry in all_entries
        ]
        
        try:
            retriever = await get_semantic_retriever()
            search_results = await retriever.hybrid_search(
                query=query,
                memories=memories_data,
                agent_id=agent_id,
                k=max_results
            )
            
            result_ids = [r.memory_id for r in search_results]
            id_to_entry = {entry.id: entry for entry in all_entries}
            
            return [
                self._to_pydantic(id_to_entry[rid])
                for rid in result_ids
                if rid in id_to_entry
            ]
        except Exception:
            return await self._keyword_retrieve(agent_id, query, level, max_results)
    
    async def _promote_if_needed(self, agent_id: str) -> None:
        """检查并晋升符合条件的记忆"""
        try:
            all_memories = await self.get_agent_memories(agent_id)
            
            memories_data = [
                {
                    "id": m.id,
                    "level": m.level,
                    "content": m.content,
                    "usage_count": m.usage_count,
                    "relevance_score": m.relevance_score,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "last_accessed_at": m.last_accessed_at.isoformat() if m.last_accessed_at else None,
                }
                for m in all_memories
            ]
            
            candidates = promotion_service.get_promotion_candidates(memories_data)
            
            for memory_data, target_level in candidates[:5]:
                await self.promote_memory(memory_data["id"], target_level)
        except Exception:
            pass
    
    async def promote_memory(self, memory_id: str, target_level: str) -> bool:
        """手动晋升记忆"""
        result = await self.db.execute(
            select(MemoryEntryModel).where(MemoryEntryModel.id == memory_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            return False
        
        old_level = entry.level
        entry.level = target_level
        entry.last_accessed_at = datetime.now()
        
        await self.db.commit()
        
        if self.use_semantic_search:
            try:
                retriever = await get_semantic_retriever()
                await retriever.remove_from_index(memory_id)
                await retriever.index_memory(
                    memory_id=memory_id,
                    content=entry.content,
                    metadata={
                        "agent_id": entry.agent_id,
                        "level": target_level,
                        "tags": entry.tags or [],
                        "source": entry.source,
                        "session_id": entry.session_id,
                    }
                )
            except Exception:
                pass
        
        return True
    
    async def _keyword_retrieve(
        self,
        agent_id: str,
        query: str,
        level: Optional[str],
        max_results: int
    ) -> List[PydanticMemoryEntry]:
        """关键词检索 - MVP 实现"""
        query_lower = query.lower()
        keywords = query_lower.split()
        
        query_stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.agent_id == agent_id
        )
        
        if level:
            query_stmt = query_stmt.where(MemoryEntryModel.level == level)
        
        result = await self.db.execute(query_stmt)
        all_entries = result.scalars().all()
        
        relevant = []
        for entry in all_entries:
            score = self._calculate_relevance(entry, keywords, query_lower)
            if score > 0:
                relevant.append((self._to_pydantic(entry), score))
        
        relevant.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in relevant[:max_results]]
    
    def _calculate_relevance(
        self,
        entry: MemoryEntryModel,
        keywords: List[str],
        query: str
    ) -> float:
        """计算记忆相关性分数"""
        score = 0.0
        
        tags = entry.tags or []
        for tag in tags:
            if tag.lower() in query:
                score += 2.0
        
        content_lower = entry.content.lower()
        for keyword in keywords:
            if keyword in content_lower:
                score += 1.0
        
        if entry.relevance_score:
            score += entry.relevance_score * 0.5
        
        return score
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        relevance_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[PydanticMemoryEntry]:
        """更新记忆"""
        update_data = {"last_accessed_at": datetime.now()}
        
        if content is not None:
            update_data["content"] = content
        if tags is not None:
            update_data["tags"] = tags
        if relevance_score is not None:
            update_data["relevance_score"] = relevance_score
        if metadata is not None:
            update_data["metadata"] = metadata
        
        await self.db.execute(
            update(MemoryEntryModel)
            .where(MemoryEntryModel.id == memory_id)
            .values(**update_data)
        )
        await self.db.commit()
        
        return await self.get_memory(memory_id)
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if self.use_semantic_search:
            try:
                retriever = await get_semantic_retriever()
                await retriever.remove_from_index(memory_id)
            except Exception:
                pass
        
        result = await self.db.execute(
            delete(MemoryEntryModel).where(MemoryEntryModel.id == memory_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def promote_memory(
        self,
        memory_id: str,
        to_level: str
    ) -> Optional[PydanticMemoryEntry]:
        """提升记忆到更高层级"""
        await self.db.execute(
            update(MemoryEntryModel)
            .where(MemoryEntryModel.id == memory_id)
            .values(level=to_level, last_accessed_at=datetime.now())
        )
        await self.db.commit()
        
        return await self.get_memory(memory_id)
    
    async def get_agent_context(
        self,
        agent_id: str
    ) -> Optional[AgentContextModel]:
        """获取 Agent 上下文"""
        result = await self.db.execute(
            select(AgentContextModel).where(
                AgentContextModel.agent_id == agent_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_context(
        self,
        agent_id: str,
        role: str,
        system_prompt: str = "",
        personality: Dict[str, Any] = None,
        session_id: str = None
    ) -> AgentContextModel:
        """创建或更新 Agent 上下文"""
        existing = await self.get_agent_context(agent_id)
        
        if existing:
            existing.role = role
            existing.system_prompt = system_prompt
            existing.personality = personality or {}
            existing.session_id = session_id
            existing.last_active_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        else:
            context = AgentContextModel(
                agent_id=agent_id,
                role=role,
                system_prompt=system_prompt,
                personality=personality or {},
                session_id=session_id,
                created_at=datetime.now(),
                last_active_at=datetime.now()
            )
            self.db.add(context)
            await self.db.commit()
            await self.db.refresh(context)
            return context
    
    def _to_pydantic(self, entry: MemoryEntryModel) -> PydanticMemoryEntry:
        """转换为 Pydantic 模型"""
        return PydanticMemoryEntry(
            id=entry.id,
            content=entry.content,
            level=entry.level,
            tags=entry.tags or [],
            relevance_score=entry.relevance_score or 1.0,
            created_at=entry.created_at,
            last_accessed_at=entry.last_accessed_at
        )
    
    async def generate_summary(self, agent_id: str) -> str:
        """
        生成会话摘要 - 简化实现
        
        Phase 4.2 可升级为 LLM 摘要
        """
        recent_memories = await self.get_agent_memories(
            agent_id,
            level=MemoryLevel.WORKING,
            limit=20
        )
        
        if not recent_memories:
            return ""
        
        topics = set()
        for mem in recent_memories:
            if len(mem.content) > 10:
                topics.add(mem.content[:50])
        
        if topics:
            return f"会话要点: {', '.join(list(topics)[:5])}"
        return ""
    
    # ===== 高级记忆管理方法 =====
    
    async def refresh_memory_scores(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        刷新记忆分数并可能触发晋升
        
        Returns:
            统计信息
        """
        memories = await self.get_agent_memories(agent_id)
        
        stats = {
            "total": len(memories),
            "promoted": 0,
            "updated_scores": 0,
        }
        
        for mem in memories:
            mem_data = {
                "id": mem.id,
                "level": mem.level,
                "content": mem.content,
                "usage_count": mem.usage_count,
                "relevance_score": mem.relevance_score,
                "created_at": mem.created_at.isoformat() if mem.created_at else None,
                "last_accessed_at": mem.last_accessed_at.isoformat() if mem.last_accessed_at else None,
            }
            
            enhanced = memory_enhancer.enhance_memory(mem_data)
            new_relevance = enhanced["_quality"]["relevance"]
            
            if new_relevance != mem.relevance_score:
                await self.db.execute(
                    update(MemoryEntryModel)
                    .where(MemoryEntryModel.id == mem.id)
                    .values(
                        relevance_score=new_relevance,
                        last_accessed_at=datetime.now(),
                    )
                )
                stats["updated_scores"] += 1
        
        candidates = promotion_service.get_promotion_candidates([
            {
                "id": m.id,
                "level": m.level,
                "content": m.content,
                "usage_count": m.usage_count,
                "relevance_score": m.relevance_score,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ])
        
        for mem_data, target_level in candidates[:10]:
            if await self.promote_memory(mem_data["id"], target_level):
                stats["promoted"] += 1
        
        await self.db.commit()
        return stats
    
    async def deduplicate_memories(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        检查并合并重复记忆
        
        Returns:
            去重统计
        """
        memories = await self.get_agent_memories(agent_id)
        
        memories_data = [
            {
                "id": m.id,
                "content": m.content,
                "tags": m.tags or [],
                "created_at": m.created_at,
                "usage_count": m.usage_count,
            }
            for m in memories
        ]
        
        duplicates = memory_enhancer.deduplicator.find_duplicates(memories_data)
        
        result = {
            "total_groups": len(duplicates),
            "merged_count": 0,
            "removed_ids": [],
        }
        
        for group in duplicates:
            if len(group) < 2:
                continue
            
            merged = memory_enhancer.deduplicator.merge_memories(group, strategy="combined")
            
            keep_id = group[0]["id"]
            remove_ids = [m["id"] for m in group[1:]]
            
            await self.update_memory(
                keep_id,
                content=merged["content"],
                tags=merged.get("tags"),
            )
            
            for remove_id in remove_ids:
                await self.delete_memory(remove_id)
                result["removed_ids"].append(remove_id)
                result["merged_count"] += 1
            
            if self.use_semantic_search:
                try:
                    retriever = await get_semantic_retriever()
                    for remove_id in remove_ids:
                        await retriever.remove_from_index(remove_id)
                except Exception:
                    pass
        
        await self.db.commit()
        return result
    
    async def get_memory_quality(
        self,
        memory_id: str,
    ) -> Optional[Dict]:
        """获取记忆质量评分"""
        mem = await self.get_memory(memory_id)
        if not mem:
            return None
        
        quality = memory_enhancer.calculate_quality({
            "created_at": mem.created_at,
            "last_accessed_at": mem.last_accessed_at,
            "usage_count": mem.usage_count,
            "relevance_score": mem.relevance_score,
        })
        
        return {
            "memory_id": memory_id,
            "quality": {
                "freshness": quality.freshness_score,
                "relevance": quality.relevance_score,
                "utility": quality.utility_score,
                "overall": quality.overall_quality,
            }
        }
    
    async def get_sensitive_memories(
        self,
        agent_id: str,
    ) -> List[Dict]:
        """获取标记为敏感的记忆"""
        memories = await self.get_agent_memories(agent_id)
        sensitive = []
        
        for mem in memories:
            enhanced = memory_enhancer.enhance_memory({
                "content": mem.content,
            })
            if enhanced.get("_sensitive"):
                sensitive.append({
                    "id": mem.id,
                    "content": mem.content[:50] + "..." if len(mem.content) > 50 else mem.content,
                    "sensitive_types": enhanced.get("_sensitive_types", []),
                    "level": mem.level,
                })
        
        return sensitive
    
    async def auto_forget(
        self,
        agent_id: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        自动遗忘低质量或过期记忆
        
        Args:
            agent_id: Agent ID
            dry_run: 是否只返回计划不实际删除
            
        Returns:
            遗忘结果
        """
        memories = await self.get_agent_memories(agent_id)
        
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
        
        if dry_run:
            plan = forget_service.get_forget_plan(memories_data, agent_id)
            capacity_status = capacity_manager.check_capacity(memories_data)
            return {
                "agent_id": agent_id,
                "dry_run": True,
                "forget_plan": plan,
                "capacity_status": capacity_status,
            }
        
        quality_forget_ids = forget_service.select_memories_to_forget(memories_data, agent_id)
        capacity_forget_ids = capacity_manager.get_memories_to_remove(memories_data)
        
        all_forget_ids = list(set(quality_forget_ids + capacity_forget_ids))
        
        deleted_count = 0
        for mem_id in all_forget_ids:
            if await self.delete_memory(mem_id):
                deleted_count += 1
                
                if self.use_semantic_search:
                    try:
                        retriever = await get_semantic_retriever()
                        await retriever.remove_from_index(mem_id)
                    except Exception:
                        pass
        
        return {
            "agent_id": agent_id,
            "dry_run": False,
            "total_checked": len(memories_data),
            "quality_forgotten": len(quality_forget_ids),
            "capacity_forgotten": len(capacity_forget_ids),
            "total_forgotten": deleted_count,
        }
    
    async def get_forget_plan(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """获取遗忘计划"""
        memories = await self.get_agent_memories(agent_id)
        
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
        
        plan = forget_service.get_forget_plan(memories_data, agent_id)
        capacity_status = capacity_manager.check_capacity(memories_data)
        
        return {
            "agent_id": agent_id,
            "forget_plan": plan,
            "capacity_status": capacity_status,
        }
    
    async def check_capacity(self, agent_id: str) -> Dict[str, Any]:
        """检查记忆容量状态"""
        memories = await self.get_agent_memories(agent_id)
        
        memories_data = [
            {
                "id": m.id,
                "level": m.level,
                "content": m.content,
                "relevance_score": m.relevance_score,
                "usage_count": m.usage_count,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "last_accessed_at": m.last_accessed_at.isoformat() if m.last_accessed_at else None,
            }
            for m in memories
        ]
        
        return capacity_manager.check_capacity(memories_data)
    
    async def compress_context(
        self,
        agent_id: str,
        max_tokens: int = 4096,
        strategy: str = "auto",
    ) -> Dict[str, Any]:
        """
        压缩Agent的上下文记忆
        
        Args:
            agent_id: Agent ID
            max_tokens: 最大token数
            strategy: 压缩策略 (auto/summary/importance/token_limit/merge_adjacent/truncate)
        
        Returns:
            压缩结果
        """
        memories = await self.get_agent_memories(agent_id)
        
        messages = [
            {
                "role": "assistant" if m.level == MemoryLevel.WORKING else "user",
                "content": m.content,
                "memory_id": m.id,
                "level": m.level,
            }
            for m in memories
        ]
        
        result = await context_compressor.compress(
            messages,
            max_tokens=max_tokens,
        )
        
        return {
            "agent_id": agent_id,
            "original_tokens": result.original_tokens,
            "compressed_tokens": result.compressed_tokens,
            "compression_ratio": result.compression_ratio,
            "strategy": result.strategy.value,
            "messages_removed": result.messages_removed,
            "messages_merged": result.messages_merged,
            "summary": result.summary_text,
            "compressed_messages": result.compressed_messages,
        }
    
    async def get_compressed_context_prompt(
        self,
        agent_id: str,
        max_tokens: int = 4096,
    ) -> str:
        """
        获取压缩后的上下文提示词
        
        Args:
            agent_id: Agent ID
            max_tokens: 最大token数
            
        Returns:
            压缩后的上下文提示词
        """
        result = await self.compress_context(agent_id, max_tokens)
        
        if result.get("summary"):
            return f"# 对话摘要\n{result['summary']}\n\n# 最近对话\n" + "\n\n".join(
                f"- {m.get('content', '')}" for m in result.get("compressed_messages", [])[-3:]
            )
        
        return "\n\n".join(
            f"- {m.get('content', '')}" for m in result.get("compressed_messages", [])
        )
    
    async def get_context_prompt(self, agent_id: str) -> str:
        """
        生成上下文提示词 - 组合各层记忆
        
        参考 LangChain 的 get_context 方法
        """
        parts = []
        
        working_memories = await self.get_agent_memories(
            agent_id,
            level=MemoryLevel.WORKING,
            limit=5
        )
        if working_memories:
            parts.append("# Working Memory (L1)")
            for mem in working_memories:
                parts.append(f"- {mem.content}")
        
        short_term_memories = await self.get_agent_memories(
            agent_id,
            level=MemoryLevel.SHORT_TERM,
            limit=3
        )
        if short_term_memories:
            parts.append("\n# Short-term Memory (L2)")
            for mem in short_term_memories:
                parts.append(f"- {mem.content}")
        
        long_term_memories = await self.get_agent_memories(
            agent_id,
            level=MemoryLevel.LONG_TERM,
            limit=2
        )
        if long_term_memories:
            parts.append("\n# Long-term Memory (L3)")
            for mem in long_term_memories:
                parts.append(f"- {mem.content}")
        
        return "\n".join(parts) if parts else ""
    
    async def get_statistics(self, agent_id: str) -> Dict[str, int]:
        """获取 Agent 的记忆统计"""
        working = await self.get_agent_memories(
            agent_id, level=MemoryLevel.WORKING
        )
        short_term = await self.get_agent_memories(
            agent_id, level=MemoryLevel.SHORT_TERM
        )
        long_term = await self.get_agent_memories(
            agent_id, level=MemoryLevel.LONG_TERM
        )
        
        return {
            "working": len(working),
            "short_term": len(short_term),
            "long_term": len(long_term),
            "total": len(working) + len(short_term) + len(long_term)
        }
