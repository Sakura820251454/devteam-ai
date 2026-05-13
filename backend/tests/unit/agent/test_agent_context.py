"""
Agent 上下文与记忆系统单元测试
"""
import pytest
from datetime import datetime
from typing import List, Dict

from app.models.agent_context import (
    AgentContext,
    AgentMemoryManager,
    MemoryLevel,
    MemoryEntry,
    AgentContextFactory,
    SharedSessionContext
)
from app.services.shared.soul_parser import SoulFile


class TestMemoryLevel:
    """记忆层级枚举测试"""
    
    def test_memory_level_values(self):
        """测试记忆层级值"""
        assert MemoryLevel.WORKING.value == "working"
        assert MemoryLevel.SHORT_TERM.value == "short_term"
        assert MemoryLevel.LONG_TERM.value == "long_term"


class TestMemoryEntry:
    """记忆条目测试"""
    
    def test_memory_entry_creation(self):
        """测试记忆条目创建"""
        entry = MemoryEntry(
            id="test_id",
            content="Test content",
            level=MemoryLevel.WORKING,
            tags=["tag1", "tag2"],
            relevance_score=0.8
        )
        
        assert entry.id == "test_id"
        assert entry.content == "Test content"
        assert entry.level == MemoryLevel.WORKING
        assert entry.tags == ["tag1", "tag2"]
        assert entry.relevance_score == 0.8
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.last_accessed_at, datetime)


class TestAgentContext:
    """Agent 上下文测试"""
    
    def test_context_creation(self):
        """测试上下文创建"""
        context = AgentContext(
            agent_id="test_agent",
            session_id="test_session",
            role="backend",
            system_prompt="You are a backend developer"
        )
        
        assert context.agent_id == "test_agent"
        assert context.session_id == "test_session"
        assert context.role == "backend"
        assert context.system_prompt == "You are a backend developer"
        assert context.status == "idle"
        assert context.current_task is None
        assert context.task_progress == 0.0
        assert context.conversation_history == []
        assert context.memory_entries == []
        assert context.context_window == []
    
    def test_context_with_personality(self):
        """测试带个性的上下文"""
        context = AgentContext(
            agent_id="test_agent",
            session_id="test_session",
            role="pm",
            system_prompt="You are a PM",
            personality={
                "core_principles": ["Be user-centric"],
                "execution_rules": ["Plan first"]
            }
        )
        
        assert "core_principles" in context.personality
        assert "execution_rules" in context.personality
        assert "Be user-centric" in context.personality["core_principles"]


class TestAgentMemoryManager:
    """Agent 记忆管理器测试"""
    
    def setup_method(self):
        """设置测试上下文"""
        self.context = AgentContext(
            agent_id="test_agent",
            session_id="test_session",
            role="test",
            system_prompt="Test prompt"
        )
        self.memory_manager = AgentMemoryManager(self.context)
    
    def test_add_working_memory(self):
        """测试添加工作记忆"""
        self.memory_manager.add_memory("Test working memory", MemoryLevel.WORKING, ["test"])
        
        assert len(self.context.memory_entries) == 1
        assert self.context.memory_entries[0].content == "Test working memory"
        assert self.context.memory_entries[0].level == MemoryLevel.WORKING
        assert "test" in self.context.memory_entries[0].tags
        
        # 工作记忆应添加到上下文窗口
        assert len(self.context.context_window) == 1
    
    def test_add_short_term_memory(self):
        """测试添加短期记忆"""
        self.memory_manager.add_memory("Test short term memory", MemoryLevel.SHORT_TERM)
        
        assert len(self.context.memory_entries) == 1
        assert self.context.memory_entries[0].level == MemoryLevel.SHORT_TERM
        # 短期记忆不应添加到上下文窗口
        assert len(self.context.context_window) == 0
    
    def test_add_long_term_memory(self):
        """测试添加长期记忆"""
        self.memory_manager.add_memory("Test long term memory", MemoryLevel.LONG_TERM, ["knowledge"])
        
        assert len(self.context.memory_entries) == 1
        assert self.context.memory_entries[0].level == MemoryLevel.LONG_TERM
    
    def test_retrieve_relevant_memory(self):
        """测试检索相关记忆"""
        # 添加一些记忆
        self.memory_manager.add_memory("Python is great", MemoryLevel.WORKING, ["python", "programming"])
        self.memory_manager.add_memory("JavaScript is fun", MemoryLevel.WORKING, ["javascript", "programming"])
        self.memory_manager.add_memory("Coffee is good", MemoryLevel.WORKING, ["coffee", "drink"])
        
        # 检索与 programming 相关的记忆
        results = self.memory_manager.retrieve_relevant_memory("programming")
        
        assert len(results) >= 2
        content_list = [r.content for r in results]
        assert "Python is great" in content_list
        assert "JavaScript is fun" in content_list
    
    def test_retrieve_relevant_memory_empty(self):
        """测试检索无结果"""
        results = self.memory_manager.retrieve_relevant_memory("nonexistent")
        assert len(results) == 0
    
    def test_context_window_truncation(self):
        """测试上下文窗口截断"""
        # 添加大量内容
        for i in range(20):
            self.memory_manager.add_memory(f"Message {i}" * 100, MemoryLevel.WORKING)
        
        # 确保窗口大小在限制内
        total_tokens = sum(len(text) // 4 for text in self.context.context_window)
        assert total_tokens <= self.context.max_context_tokens
    
    def test_get_context_prompt(self):
        """测试获取上下文提示词"""
        self.memory_manager.add_memory("Working memory content", MemoryLevel.WORKING)
        self.memory_manager.add_memory("Short term summary", MemoryLevel.SHORT_TERM)
        
        prompt = self.memory_manager.get_context_prompt()
        
        assert "# Working Memory" in prompt
        assert "Working memory content" in prompt
        assert "# Recent Learnings" in prompt
        assert "Short term summary" in prompt
    
    def test_summarize_conversation(self):
        """测试会话摘要"""
        # 添加对话历史
        for i in range(5):
            self.context.conversation_history.append({
                "content": f"Message {i}: This is a test message"
            })
        
        self.memory_manager.summarize_conversation()
        
        # 应该生成摘要并添加到短期记忆
        short_term_memories = [
            e for e in self.context.memory_entries
            if e.level == MemoryLevel.SHORT_TERM
        ]
        assert len(short_term_memories) >= 1


class TestAgentContextFactory:
    """Agent 上下文工厂测试"""
    
    def test_create_context(self):
        """测试创建上下文"""
        context = AgentContextFactory.create(
            agent_id="agent1",
            session_id="session1",
            role="backend",
            system_prompt="You are backend"
        )
        
        assert context.agent_id == "agent1"
        assert context.session_id == "session1"
        assert context.role == "backend"
        assert context.system_prompt == "You are backend"
    
    def test_from_soul_dict(self):
        """测试从字典格式的 soul 数据创建上下文"""
        soul_dict = {
            "name": "test_agent",
            "role": "frontend",
            "system_prompt": "You are frontend",
            "core_principles": ["Be creative"],
            "execution_rules": ["Design first"]
        }
        
        context = AgentContextFactory.from_soul(soul_dict, "session1")
        
        assert context.agent_id == "test_agent"
        assert context.role == "frontend"
        assert "Be creative" in context.personality["core_principles"]
    
    def test_from_soul_file(self):
        """测试从 SoulFile 对象创建上下文"""
        soul_file = SoulFile(
            name="frontend_dev",
            role="frontend",
            title="Senior Frontend Developer",
            core_principles=["Focus on UX", "Write clean code"],
            execution_rules=["Test first", "Review code"]
        )
        
        context = AgentContextFactory.from_soul_file(soul_file, "session1")
        
        assert context.agent_id == "frontend_dev"
        assert context.role == "frontend"
        assert "Focus on UX" in context.personality["core_principles"]
        assert "Test first" in context.personality["execution_rules"]
        assert context.soul_data == soul_file


class TestSharedSessionContext:
    """共享会话上下文测试"""
    
    def test_create_shared_context(self):
        """测试创建共享上下文"""
        shared = SharedSessionContext(session_id="session1")
        
        assert shared.session_id == "session1"
        assert shared.participants == []
        assert shared.shared_knowledge == []
        assert shared.team_goals == []
    
    def test_add_shared_knowledge(self):
        """测试添加共享知识"""
        shared = SharedSessionContext(session_id="session1")
        
        shared.add_shared_knowledge("Project deadline is Friday")
        shared.add_shared_knowledge("Use React for frontend")
        
        assert len(shared.shared_knowledge) == 2
        assert "Project deadline is Friday" in shared.shared_knowledge
        
        # 重复添加不应重复
        shared.add_shared_knowledge("Project deadline is Friday")
        assert len(shared.shared_knowledge) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
