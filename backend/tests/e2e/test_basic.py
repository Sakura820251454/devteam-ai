"""
DevTeam-AI 基础测试

测试核心功能：
1. Agent 模型创建
2. Mock LLM 调用
3. API 接口
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.agent import Agent, AgentConfig, PersonalityType, CommunicationStyle, SkillLevel
from app.core.mock_llm import MockLLMProvider, create_mock_provider


@pytest.fixture
def agent_config():
    return AgentConfig(
        name="测试Agent",
        role="开发者",
        title="高级工程师",
        backstory="5年Python开发经验",
        personality_type=PersonalityType.RIGOROUS,
        communication_style=CommunicationStyle.DETAILED,
        skills={"Python": SkillLevel.MASTERED}
    )


@pytest.fixture
def agent(agent_config):
    return Agent(id="test-agent-001", config=agent_config)


class TestAgentModel:
    """测试 Agent 模型"""
    
    def test_create_agent(self, agent):
        assert agent.id == "test-agent-001"
        assert agent.config.name == "测试Agent"
        assert agent.config.role == "开发者"
    
    def test_build_system_prompt(self, agent):
        prompt = agent.build_system_prompt()
        assert "测试Agent" in prompt
        assert "开发者" in prompt
        assert "Python" in prompt
        assert "高级工程师" in prompt


class TestMockLLM:
    """测试 Mock LLM"""
    
    @pytest.mark.asyncio
    async def test_mock_chat(self):
        provider = await create_mock_provider()
        async with provider:
            from app.core.llm import Message
            messages = [Message("user", "你好")]
            response = await provider.chat(messages)
            
            assert response.content is not None
            assert len(response.content) > 0
            assert response.finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_mock_stream(self):
        provider = await create_mock_provider()
        async with provider:
            from app.core.llm import Message
            messages = [Message("user", "你好")]
            
            chunks = []
            async for chunk in provider.stream_chat(messages):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            full_response = "".join(chunks)
            assert len(full_response) > 0
    
    @pytest.mark.asyncio
    async def test_mock_stats(self):
        provider = await create_mock_provider()
        async with provider:
            from app.core.llm import Message
            messages = [Message("user", "测试")]
            
            initial_stats = provider.get_stats()
            assert initial_stats["call_count"] == 0
            
            await provider.chat(messages)
            
            after_stats = provider.get_stats()
            assert after_stats["call_count"] == 1
            
            provider.reset_stats()
            reset_stats = provider.get_stats()
            assert reset_stats["call_count"] == 0


class TestAPI:
    """测试 API 接口"""
    
    @pytest.mark.asyncio
    async def test_root(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "DevTeam-AI"
            assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_health(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_init_default_agent(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/agents/init-default")
            assert response.status_code == 200
            data = response.json()
            assert "agent" in data
            assert data["agent"]["name"] is not None
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={"title": "测试会话"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "测试会话"
            assert data["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_list_sessions(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/sessions")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
    
    @pytest.mark.asyncio
    async def test_full_chat_flow(self):
        """测试完整的对话流程"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. 初始化 Agent
            init_response = await client.post("/api/agents/init-default")
            assert init_response.status_code == 200
            agent_data = init_response.json()["agent"]
            agent_id = agent_data["id"]
            
            # 2. 创建会话
            session_response = await client.post(
                "/api/sessions",
                json={"title": "测试对话"}
            )
            assert session_response.status_code == 200
            session_data = session_response.json()
            session_id = session_data["id"]
            
            # 3. 发送消息
            chat_response = await client.post(
                "/api/chat",
                json={
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "message": "你好，介绍一下自己"
                }
            )
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            assert "response" in chat_data
            assert len(chat_data["response"]) > 0
            
            # 4. 获取消息历史
            messages_response = await client.get(f"/api/sessions/{session_id}/messages")
            assert messages_response.status_code == 200
            messages = messages_response.json()
            assert len(messages) >= 2  # 用户消息 + Agent 回复


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
