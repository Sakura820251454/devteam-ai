"""
持久化 Agent 上下文管理器
集成层：将内存记忆系统与持久化系统桥接
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.models.agent_context import (
    AgentContext,
    AgentMemoryManager,
    MemoryEntry,
    MemoryLevel as PydanticMemoryLevel
)
from app.models.memory_db import MemoryLevel as DBMemoryLevel
from app.services.memory.persistent_memory_manager import PersistentMemoryManager

logger = logging.getLogger(__name__)


class PersistentAgentMemoryManager:
    """
    持久化 Agent 记忆管理器

    扩展现有的 AgentMemoryManager，同时维护：
    1. 内存中的记忆（用于快速访问）
    2. 数据库中的记忆（用于持久化）

    两种操作会自动同步
    """

    def __init__(self, agent_context: AgentContext, db_session=None):
        """
        初始化持久化记忆管理器

        Args:
            agent_context: 现有的 Agent 上下文
            db_session: 可选的数据库会话
        """
        self.context = agent_context
        self.memory_manager = AgentMemoryManager(agent_context)
        self.db_session = db_session
        self.persistent_manager = None

        if db_session:
            self.persistent_manager = PersistentMemoryManager(db_session)

    def add_memory(
        self,
        content: str,
        level: PydanticMemoryLevel = PydanticMemoryLevel.WORKING,
        tags: List[str] = None,
        sync: bool = True
    ):
        """
        添加记忆（同时添加到内存和数据库）

        Args:
            content: 记忆内容
            level: 记忆层级
            tags: 标签列表
            sync: 是否同步到数据库
        """
        tags = tags or []

        # 1. 添加到内存
        self.memory_manager.add_memory(content, level, tags)

        # 2. 如果有数据库会话，同步到数据库
        if sync and self.persistent_manager and self.context.agent_id:
            # 异步添加（不阻塞）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(
                        self.persistent_manager.add_memory(
                            agent_id=self.context.agent_id,
                            content=content,
                            level=level.value if hasattr(level, 'value') else level,
                            tags=tags,
                            source="agent_context"
                        )
                    )
                else:
                    loop.run_until_complete(
                        self.persistent_manager.add_memory(
                            agent_id=self.context.agent_id,
                            content=content,
                            level=level.value if hasattr(level, 'value') else level,
                            tags=tags,
                            source="agent_context"
                        )
                    )
            except Exception:
                # 数据库操作失败不影响内存操作
                logger.warning("持久化记忆存储失败", exc_info=True)
    
    def retrieve_relevant_memory(
        self,
        query: str,
        max_results: int = 5,
        use_db: bool = False
    ) -> List[MemoryEntry]:
        """
        检索相关记忆
        
        Args:
            query: 查询文本
            max_results: 最大返回数量
            use_db: 是否使用数据库检索（更准确但更慢）
        """
        if use_db and self.persistent_manager:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    future = loop.create_task(
                        self.persistent_manager.retrieve_memory(
                            agent_id=self.context.agent_id,
                            query=query,
                            max_results=max_results
                        )
                    )
                    return future.result(timeout=5) if future.done() else []
                else:
                    return loop.run_until_complete(
                        self.persistent_manager.retrieve_memory(
                            agent_id=self.context.agent_id,
                            query=query,
                            max_results=max_results
                        )
                    )
            except Exception:
                logger.warning("持久化语义检索失败，回退到内存检索", exc_info=True)

        # 使用内存检索（快速）
        return self.memory_manager.retrieve_relevant_memory(query, max_results)
    
    def get_context_prompt(self) -> str:
        """生成上下文提示词"""
        return self.memory_manager.get_context_prompt()
    
    def summarize_conversation(self):
        """生成会话摘要"""
        self.memory_manager.summarize_conversation()
    
    def sync_from_db(self):
        """从数据库加载记忆到内存"""
        if not self.persistent_manager:
            return
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            
            # 获取数据库中的记忆
            if loop.is_running():
                future = loop.create_task(
                    self.persistent_manager.get_agent_memories(self.context.agent_id)
                )
                db_memories = future.result(timeout=5) if future.done() else []
            else:
                db_memories = loop.run_until_complete(
                    self.persistent_manager.get_agent_memories(self.context.agent_id)
                )
            
            # 合并到内存（去重）
            memory_ids = {mem.id for mem in self.context.memory_entries}
            
            for db_mem in db_memories:
                if db_mem.id not in memory_ids:
                    # 转换为内存中的格式
                    level_map = {
                        "working": PydanticMemoryLevel.WORKING,
                        "short_term": PydanticMemoryLevel.SHORT_TERM,
                        "long_term": PydanticMemoryLevel.LONG_TERM
                    }
                    level = level_map.get(db_mem.level, PydanticMemoryLevel.WORKING)
                    
                    self.context.memory_entries.append(
                        MemoryEntry(
                            id=db_mem.id,
                            content=db_mem.content,
                            level=level,
                            tags=db_mem.tags,
                            relevance_score=db_mem.relevance_score,
                            created_at=db_mem.created_at,
                            last_accessed_at=db_mem.last_accessed_at
                        )
                    )
                    memory_ids.add(db_mem.id)
            
        except Exception as e:
            print(f"Failed to sync from DB: {e}")
    
    def sync_to_db(self):
        """将内存中的记忆同步到数据库"""
        if not self.persistent_manager:
            return
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            
            for mem in self.context.memory_entries:
                level_str = mem.level.value if hasattr(mem.level, 'value') else mem.level
                
                if loop.is_running():
                    loop.create_task(
                        self.persistent_manager.add_memory(
                            agent_id=self.context.agent_id,
                            content=mem.content,
                            level=level_str,
                            tags=mem.tags,
                            source="sync"
                        )
                    )
                else:
                    loop.run_until_complete(
                        self.persistent_manager.add_memory(
                            agent_id=self.context.agent_id,
                            content=mem.content,
                            level=level_str,
                            tags=mem.tags,
                            source="sync"
                        )
                    )
        except Exception as e:
            print(f"Failed to sync to DB: {e}")


class PersistentAgentContextFactory:
    """持久化 Agent 上下文工厂"""
    
    @staticmethod
    def create(
        agent_id: str,
        session_id: str,
        role: str,
        system_prompt: str,
        db_session=None
    ) -> AgentContext:
        """
        创建持久化的 Agent 上下文
        
        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            role: 角色
            system_prompt: 系统提示词
            db_session: 数据库会话
            
        Returns:
            AgentContext: Agent 上下文
        """
        # 1. 创建基本的 AgentContext
        context = AgentContext(
            agent_id=agent_id,
            session_id=session_id,
            role=role,
            system_prompt=system_prompt
        )
        
        # 2. 如果有数据库会话，创建持久化管理器
        if db_session:
            context._persistent_memory_manager = PersistentAgentMemoryManager(
                context,
                db_session
            )
            
            # 3. 尝试从数据库加载已有的记忆
            context._persistent_memory_manager.sync_from_db()
        
        return context
    
    @staticmethod
    def create_with_soul(
        soul_data: dict,
        session_id: str,
        db_session=None
    ) -> AgentContext:
        """从 soul 数据创建持久化上下文"""
        # 创建基本的 AgentContext
        context = AgentContext(
            agent_id=soul_data.get("name", "unknown"),
            session_id=session_id,
            role=soul_data.get("role", "agent"),
            system_prompt=soul_data.get("system_prompt", ""),
            personality={
                "core_principles": soul_data.get("core_principles", []),
                "execution_rules": soul_data.get("execution_rules", [])
            }
        )

        # 如果有数据库会话，创建持久化管理器
        if db_session:
            context._persistent_memory_manager = PersistentAgentMemoryManager(
                context,
                db_session
            )
            context._persistent_memory_manager.sync_from_db()

        return context
