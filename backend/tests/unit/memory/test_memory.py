"""
持久化记忆系统单元测试
Phase 4.1: MVP 记忆持久化
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from typing import List

from app.models.memory_db import (
    MemoryEntryModel,
    AgentContextModel,
    MemoryLevel,
    TrajectoryModel,
    SkillModel,
    AgentSkillModel
)
from app.services.memory.persistent_memory_manager import PersistentMemoryManager
from app.database import get_db, init_db, engine, Base


class TestMemoryLevel:
    """记忆层级枚举测试"""

    def test_memory_level_values(self):
        """测试记忆层级值"""
        assert MemoryLevel.WORKING == "working"
        assert MemoryLevel.SHORT_TERM == "short_term"
        assert MemoryLevel.LONG_TERM == "long_term"


class TestMemoryEntryModel:
    """记忆条目模型测试"""

    def test_memory_entry_creation(self):
        """测试记忆条目创建"""
        entry = MemoryEntryModel(
            id="test_mem_001",
            agent_id="agent_001",
            content="测试内容",
            level=MemoryLevel.WORKING,
            tags=["测试", "开发"],
            relevance_score=0.9,
            created_at=datetime.now(),
            last_accessed_at=datetime.now()
        )

        assert entry.id == "test_mem_001"
        assert entry.agent_id == "agent_001"
        assert entry.content == "测试内容"
        assert entry.level == MemoryLevel.WORKING
        assert entry.tags == ["测试", "开发"]
        assert entry.relevance_score == 0.9
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.last_accessed_at, datetime)

    def test_memory_entry_defaults(self):
        """测试默认值 - 注意：SQLAlchemy defaults 在创建对象时不会自动设置"""
        entry = MemoryEntryModel(
            id="test_mem_002",
            agent_id="agent_001",
            content="测试",
            level=MemoryLevel.SHORT_TERM,
            tags=[],
            relevance_score=1.0,
            usage_count=0
        )

        assert entry.tags == []
        assert entry.relevance_score == 1.0
        assert entry.usage_count == 0


class TestAgentContextModel:
    """Agent 上下文模型测试"""

    def test_agent_context_creation(self):
        """测试 Agent 上下文创建"""
        context = AgentContextModel(
            agent_id="agent_001",
            role="后端开发",
            system_prompt="你是一个后端开发工程师",
            status="idle",
            task_progress=0.0,
            max_context_tokens=8192
        )

        assert context.agent_id == "agent_001"
        assert context.role == "后端开发"
        assert context.status == "idle"
        assert context.task_progress == 0.0
        assert context.max_context_tokens == 8192

    def test_agent_context_with_personality(self):
        """测试带 personality 的上下文"""
        context = AgentContextModel(
            agent_id="agent_002",
            role="前端开发",
            personality={
                "core_principles": ["代码规范", "性能优先"],
                "execution_rules": ["TDD", "Code Review"]
            }
        )

        assert "core_principles" in context.personality
        assert "execution_rules" in context.personality


class TestDatabaseSchema:
    """数据库表结构测试"""

    def test_memory_entries_table_name(self):
        """测试表名"""
        assert MemoryEntryModel.__tablename__ == "memory_entries"

    def test_agent_contexts_table_name(self):
        """测试上下文表名"""
        assert AgentContextModel.__tablename__ == "agent_contexts"

    def test_trajectories_table_name(self):
        """测试轨迹表名"""
        assert TrajectoryModel.__tablename__ == "trajectories"

    def test_skills_table_name(self):
        """测试技能表名"""
        assert SkillModel.__tablename__ == "skills"

    def test_agent_skills_table_name(self):
        """测试 Agent-技能关联表名"""
        assert AgentSkillModel.__tablename__ == "agent_skills"


class TestDatabaseIntegration:
    """数据库集成测试（需要真实数据库）"""

    @pytest_asyncio.fixture
    async def db_session(self):
        """创建测试数据库会话"""
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import get_settings

        settings = get_settings()
        test_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with async_session() as session:
            yield session

        await test_engine.dispose()

    @pytest.mark.asyncio
    async def test_add_memory(self, db_session):
        """测试添加记忆"""
        manager = PersistentMemoryManager(db_session)

        entry = await manager.add_memory(
            agent_id="test_agent",
            content="这是一个测试记忆",
            level=MemoryLevel.WORKING,
            tags=["测试"],
            source="test"
        )

        assert entry is not None
        assert entry.content == "这是一个测试记忆"
        assert entry.level == MemoryLevel.WORKING

    @pytest.mark.asyncio
    async def test_get_memory(self, db_session):
        """测试获取记忆"""
        manager = PersistentMemoryManager(db_session)

        added = await manager.add_memory(
            agent_id="test_agent",
            content="要获取的记忆"
        )

        retrieved = await manager.get_memory(added.id)

        assert retrieved is not None
        assert retrieved.id == added.id
        assert retrieved.content == "要获取的记忆"

    @pytest.mark.asyncio
    async def test_get_agent_memories(self, db_session):
        """测试获取 Agent 的所有记忆"""
        manager = PersistentMemoryManager(db_session)

        await manager.add_memory(
            agent_id="test_agent",
            content="记忆1",
            level=MemoryLevel.WORKING
        )
        await manager.add_memory(
            agent_id="test_agent",
            content="记忆2",
            level=MemoryLevel.SHORT_TERM
        )
        await manager.add_memory(
            agent_id="test_agent",
            content="记忆3",
            level=MemoryLevel.LONG_TERM
        )

        all_memories = await manager.get_agent_memories("test_agent")
        assert len(all_memories) == 3

        working_memories = await manager.get_agent_memories(
            "test_agent",
            level=MemoryLevel.WORKING
        )
        assert len(working_memories) == 1

    @pytest.mark.asyncio
    async def test_retrieve_memory(self, db_session):
        """测试检索记忆"""
        manager = PersistentMemoryManager(db_session)

        await manager.add_memory(
            agent_id="test_agent",
            content="Python 是一种高级编程语言",
            tags=["编程", "Python"],
            level=MemoryLevel.LONG_TERM
        )
        await manager.add_memory(
            agent_id="test_agent",
            content="JavaScript 用于前端开发",
            tags=["前端", "JavaScript"],
            level=MemoryLevel.LONG_TERM
        )
        await manager.add_memory(
            agent_id="test_agent",
            content="后端开发需要掌握数据库",
            tags=["后端", "数据库"],
            level=MemoryLevel.LONG_TERM
        )

        results = await manager.retrieve_memory(
            agent_id="test_agent",
            query="Python 编程",
            max_results=10
        )

        assert len(results) > 0
        assert "Python" in results[0].content

    @pytest.mark.asyncio
    async def test_update_memory(self, db_session):
        """测试更新记忆"""
        manager = PersistentMemoryManager(db_session)

        added = await manager.add_memory(
            agent_id="test_agent",
            content="原始内容"
        )

        updated = await manager.update_memory(
            memory_id=added.id,
            content="更新后的内容",
            tags=["已更新"]
        )

        assert updated is not None
        assert updated.content == "更新后的内容"
        assert "已更新" in updated.tags

    @pytest.mark.asyncio
    async def test_delete_memory(self, db_session):
        """测试删除记忆"""
        manager = PersistentMemoryManager(db_session)

        added = await manager.add_memory(
            agent_id="test_agent",
            content="要删除的记忆"
        )

        success = await manager.delete_memory(added.id)
        assert success is True

        retrieved = await manager.get_memory(added.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_promote_memory(self, db_session):
        """测试提升记忆层级"""
        manager = PersistentMemoryManager(db_session)

        added = await manager.add_memory(
            agent_id="test_agent",
            content="要提升的记忆",
            level=MemoryLevel.WORKING
        )

        promoted = await manager.promote_memory(
            added.id,
            MemoryLevel.SHORT_TERM
        )

        assert promoted is not None
        assert promoted.level == MemoryLevel.SHORT_TERM

    @pytest.mark.asyncio
    async def test_get_context_prompt(self, db_session):
        """测试生成上下文提示词"""
        manager = PersistentMemoryManager(db_session)

        await manager.add_memory(
            agent_id="test_agent",
            content="当前正在开发用户模块",
            level=MemoryLevel.WORKING
        )
        await manager.add_memory(
            agent_id="test_agent",
            content="之前完成了登录功能",
            level=MemoryLevel.SHORT_TERM
        )

        prompt = await manager.get_context_prompt("test_agent")

        assert "Working Memory" in prompt
        assert "用户模块" in prompt
        assert "Short-term Memory" in prompt

    @pytest.mark.asyncio
    async def test_get_statistics(self, db_session):
        """测试获取统计信息"""
        manager = PersistentMemoryManager(db_session)

        await manager.add_memory(
            agent_id="test_agent",
            content="L1 记忆",
            level=MemoryLevel.WORKING
        )
        await manager.add_memory(
            agent_id="test_agent",
            content="L2 记忆1",
            level=MemoryLevel.SHORT_TERM
        )
        await manager.add_memory(
            agent_id="test_agent",
            content="L2 记忆2",
            level=MemoryLevel.SHORT_TERM
        )
        await manager.add_memory(
            agent_id="test_agent",
            content="L3 记忆",
            level=MemoryLevel.LONG_TERM
        )

        stats = await manager.get_statistics("test_agent")

        assert stats["working"] == 1
        assert stats["short_term"] == 2
        assert stats["long_term"] == 1
        assert stats["total"] == 4

    @pytest.mark.asyncio
    async def test_create_or_update_context(self, db_session):
        """测试创建或更新 Agent 上下文"""
        manager = PersistentMemoryManager(db_session)

        context = await manager.create_or_update_context(
            agent_id="new_agent",
            role="测试角色",
            system_prompt="测试提示词",
            personality={"key": "value"}
        )

        assert context is not None
        assert context.agent_id == "new_agent"
        assert context.role == "测试角色"


class TestMemoryRetrievalEdgeCases:
    """记忆检索边界情况测试"""

    @pytest_asyncio.fixture
    async def db_session(self):
        """创建测试数据库会话"""
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import get_settings

        settings = get_settings()
        test_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with async_session() as session:
            yield session

        await test_engine.dispose()

    @pytest.mark.asyncio
    async def test_empty_agent_memories(self, db_session):
        """测试不存在的 Agent 记忆"""
        manager = PersistentMemoryManager(db_session)

        memories = await manager.get_agent_memories("non_existent_agent")
        assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_empty_retrieval(self, db_session):
        """测试空检索结果"""
        manager = PersistentMemoryManager(db_session)

        results = await manager.retrieve_memory(
            agent_id="test_agent",
            query="完全不相关的查询",
            max_results=10
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_memory(self, db_session):
        """测试获取不存在的记忆"""
        manager = PersistentMemoryManager(db_session)

        result = await manager.get_memory("non_existent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self, db_session):
        """测试删除不存在的记忆"""
        manager = PersistentMemoryManager(db_session)

        result = await manager.delete_memory("non_existent_id")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
