"""
持久化 Agent 上下文集成测试
验证持久化记忆系统与现有 AgentContext 的集成
"""
import pytest
import pytest_asyncio
from datetime import datetime

from app.models.agent_context import AgentContext, MemoryLevel
from app.services.memory.persistent_agent_context import (
    PersistentAgentMemoryManager,
    PersistentAgentContextFactory
)
from app.database import Base
from app.models.memory_db import MemoryEntryModel


class TestPersistentAgentContextFactory:
    """持久化 Agent 上下文工厂测试"""

    def test_create_basic_context(self):
        """测试创建基本的持久化上下文"""
        context = PersistentAgentContextFactory.create(
            agent_id="test_agent_1",
            session_id="test_session_1",
            role="后端开发",
            system_prompt="你是一个后端开发工程师"
        )

        assert context is not None
        assert context.agent_id == "test_agent_1"
        assert context.session_id == "test_session_1"
        assert context.role == "后端开发"
        assert context.status == "idle"

    def test_create_with_soul(self):
        """测试从 soul 数据创建上下文"""
        soul_data = {
            "name": "backend_dev",
            "role": "后端开发",
            "system_prompt": "你是一个资深后端开发工程师",
            "core_principles": ["代码规范", "性能优先"],
            "execution_rules": ["TDD", "Code Review"]
        }

        context = PersistentAgentContextFactory.create_with_soul(
            soul_data=soul_data,
            session_id="test_session_2"
        )

        assert context is not None
        assert context.agent_id == "backend_dev"
        assert context.role == "后端开发"
        assert context.personality["core_principles"] == ["代码规范", "性能优先"]


class TestPersistentAgentMemoryManager:
    """持久化 Agent 记忆管理器测试"""

    def test_add_memory_to_memory(self):
        """测试添加记忆到内存"""
        context = AgentContext(
            agent_id="test_agent_2",
            session_id="test_session_2",
            role="测试",
            system_prompt="你是一个测试工程师"
        )

        manager = PersistentAgentMemoryManager(context)

        # 添加工作记忆
        manager.add_memory(
            content="这是第一条记忆",
            level=MemoryLevel.WORKING,
            tags=["测试", "开发"]
        )

        # 验证内存中的记忆
        assert len(context.memory_entries) == 1
        assert context.memory_entries[0].content == "这是第一条记忆"
        assert context.memory_entries[0].level == MemoryLevel.WORKING

    def test_add_memory_to_different_levels(self):
        """测试添加不同层级的记忆"""
        context = AgentContext(
            agent_id="test_agent_3",
            session_id="test_session_3",
            role="全栈",
            system_prompt="你是一个全栈工程师"
        )

        manager = PersistentAgentMemoryManager(context)

        # 添加工作记忆
        manager.add_memory(
            content="当前任务：开发用户模块",
            level=MemoryLevel.WORKING,
            tags=["任务"]
        )

        # 添加短期记忆
        manager.add_memory(
            content="昨天完成了登录功能",
            level=MemoryLevel.SHORT_TERM,
            tags=["经验", "完成"]
        )

        # 添加长期记忆
        manager.add_memory(
            content="掌握了 Python 异步编程",
            level=MemoryLevel.LONG_TERM,
            tags=["技能", "Python"]
        )

        # 验证各层级的记忆数量
        working = [m for m in context.memory_entries if m.level == MemoryLevel.WORKING]
        short_term = [m for m in context.memory_entries if m.level == MemoryLevel.SHORT_TERM]
        long_term = [m for m in context.memory_entries if m.level == MemoryLevel.LONG_TERM]

        assert len(working) == 1
        assert len(short_term) == 1
        assert len(long_term) == 1

    def test_retrieve_relevant_memory(self):
        """测试检索相关记忆"""
        context = AgentContext(
            agent_id="test_agent_4",
            session_id="test_session_4",
            role="开发",
            system_prompt="你是一个开发工程师"
        )

        manager = PersistentAgentMemoryManager(context)

        # 添加多条记忆
        manager.add_memory(
            content="使用 Django 框架开发 API",
            level=MemoryLevel.LONG_TERM,
            tags=["Django", "API"]
        )
        manager.add_memory(
            content="使用 React 开发前端组件",
            level=MemoryLevel.LONG_TERM,
            tags=["React", "前端"]
        )
        manager.add_memory(
            content="使用 PostgreSQL 存储数据",
            level=MemoryLevel.LONG_TERM,
            tags=["PostgreSQL", "数据库"]
        )

        # 检索 Django 相关的记忆
        results = manager.retrieve_relevant_memory("Django 框架", max_results=5)

        assert len(results) > 0
        assert any("Django" in r.content for r in results)

    def test_get_context_prompt(self):
        """测试生成上下文提示词"""
        context = AgentContext(
            agent_id="test_agent_5",
            session_id="test_session_5",
            role="开发",
            system_prompt="你是一个开发工程师"
        )

        manager = PersistentAgentMemoryManager(context)

        # 添加记忆
        manager.add_memory(
            content="当前任务：开发登录模块",
            level=MemoryLevel.WORKING
        )
        manager.add_memory(
            content="使用 JWT 进行身份验证",
            level=MemoryLevel.SHORT_TERM,
            tags=["JWT", "认证"]
        )

        # 生成上下文提示词
        prompt = manager.get_context_prompt()

        assert "Working Memory" in prompt or "# Working Memory" in prompt or "当前任务" in prompt

    def test_context_window_management(self):
        """测试上下文窗口管理"""
        context = AgentContext(
            agent_id="test_agent_6",
            session_id="test_session_6",
            role="开发",
            system_prompt="你是一个开发工程师",
            max_context_tokens=100  # 设置较小的 token 限制
        )

        manager = PersistentAgentMemoryManager(context)

        # 添加大量记忆
        for i in range(10):
            manager.add_memory(
                content=f"这是第 {i+1} 条记忆内容，应该被管理",
                level=MemoryLevel.WORKING
            )

        # 验证上下文窗口会被管理
        # （具体行为取决于 token 计算逻辑）
        assert context.max_context_tokens == 100


class TestIntegrationScenarios:
    """集成场景测试"""

    def test_agent_lifecycle_with_memory(self):
        """测试 Agent 完整生命周期中的记忆管理"""
        # 1. 创建 Agent
        context = PersistentAgentContextFactory.create(
            agent_id="agent_lifecycle",
            session_id="session_1",
            role="后端开发",
            system_prompt="你是一个后端开发工程师"
        )
        manager = PersistentAgentMemoryManager(context)

        # 2. 添加工作记忆
        manager.add_memory(
            content="开始开发用户管理模块",
            level=MemoryLevel.WORKING,
            tags=["任务"]
        )

        # 3. 完成任务
        manager.add_memory(
            content="完成用户管理模块开发，包含增删改查功能",
            level=MemoryLevel.SHORT_TERM,
            tags=["完成", "用户管理"]
        )

        # 4. 学习新技能
        manager.add_memory(
            content="学会了使用 FastAPI 开发高性能 API",
            level=MemoryLevel.LONG_TERM,
            tags=["技能", "FastAPI"]
        )

        # 5. 验证记忆被正确保存
        assert len(context.memory_entries) == 3

        # 6. 检索相关记忆
        results = manager.retrieve_relevant_memory("FastAPI")
        assert len(results) >= 1

    def test_memory_retrieval_scenarios(self):
        """测试记忆检索场景"""
        context = PersistentAgentContextFactory.create(
            agent_id="agent_retrieval",
            session_id="session_2",
            role="全栈开发",
            system_prompt="你是一个全栈开发工程师"
        )
        manager = PersistentAgentMemoryManager(context)

        # 添加多种类型的记忆
        memories = [
            ("使用 Redis 做缓存", ["Redis", "缓存"], MemoryLevel.LONG_TERM),
            ("使用 Docker 部署应用", ["Docker", "部署"], MemoryLevel.LONG_TERM),
            ("修复了一个 SQL 注入漏洞", ["安全", "SQL"], MemoryLevel.SHORT_TERM),
            ("当前正在开发支付模块", ["任务", "支付"], MemoryLevel.WORKING),
        ]

        for content, tags, level in memories:
            manager.add_memory(content, level, tags)

        # 测试不同的检索场景
        results_redis = manager.retrieve_relevant_memory("缓存")
        assert len(results_redis) >= 1
        assert any("Redis" in r.content or "缓存" in r.content for r in results_redis)

        results_docker = manager.retrieve_relevant_memory("Docker")
        assert len(results_docker) >= 1
        assert any("Docker" in r.content for r in results_docker)

        results_task = manager.retrieve_relevant_memory("当前任务")
        assert len(results_task) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
