"""
Per-agent LLM 配置单元测试

覆盖:
- AgentService: create_agent / update_agent 存储 llm_config
- AgentService: agent_chat 传递 Agent 模型给 LLMService
- LLMService: chat/stream_chat 使用 agent.llm_config 覆盖默认值
- LLMService: cost tracking 记录正确的 model 名
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.agent.agent_service import AgentService
from app.services.llm.llm_service import LLMService
from app.models.agent import Agent as AgentModel, AgentConfig, LLMConfig
from app.core.llm import Message, LLMResponse


class TestAgentServiceLLMConfig:
    """AgentService 对 llm_config 的存储和传递"""

    def setup_method(self):
        self.service = AgentService()

    def test_create_agent_with_llm_config(self):
        """创建 Agent 时传入 llm_config 应被存储"""
        templates = self.service.get_all_templates()
        assert len(templates) > 0

        llm_cfg = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        agent = self.service.create_agent(templates[0]["id"], "LLM-Agent", llm_cfg)

        assert agent["llm_config"] is not None
        assert agent["llm_config"]["provider"] == "anthropic"
        assert agent["llm_config"]["model"] == "claude-sonnet-4-6"
        assert agent["llm_config"]["temperature"] == 0.3
        assert agent["llm_config"]["max_tokens"] == 4096

    def test_create_agent_without_llm_config(self):
        """创建 Agent 时不传 llm_config 应为 None"""
        templates = self.service.get_all_templates()
        agent = self.service.create_agent(templates[0]["id"], "No-LLM-Agent")

        assert agent["llm_config"] is None

    def test_create_agent_with_partial_llm_config(self):
        """llm_config 只传部分字段"""
        templates = self.service.get_all_templates()
        agent = self.service.create_agent(
            templates[0]["id"], "Partial-LLM",
            {"provider": "openai", "model": "gpt-4o"}
        )

        assert agent["llm_config"]["provider"] == "openai"
        assert agent["llm_config"]["model"] == "gpt-4o"
        assert "temperature" not in agent["llm_config"]
        assert "max_tokens" not in agent["llm_config"]

    def test_update_agent_set_llm_config(self):
        """更新 Agent 设置 llm_config"""
        templates = self.service.get_all_templates()
        agent = self.service.create_agent(templates[0]["id"], "Update-Test")
        assert agent["llm_config"] is None

        updated = self.service.update_agent(agent["id"], {
            "llm_config": {"provider": "openai", "model": "gpt-4o", "temperature": 0.8}
        })

        assert updated["llm_config"]["provider"] == "openai"
        assert updated["llm_config"]["model"] == "gpt-4o"
        assert updated["llm_config"]["temperature"] == 0.8

    def test_update_agent_clear_llm_config(self):
        """更新 Agent 清除 llm_config"""
        templates = self.service.get_all_templates()
        agent = self.service.create_agent(
            templates[0]["id"], "Clear-Test",
            {"provider": "deepseek", "model": "deepseek-chat"}
        )
        assert agent["llm_config"] is not None

        updated = self.service.update_agent(agent["id"], {"llm_config": None})

        assert updated["llm_config"] is None

    def test_update_agent_other_fields_preserve_llm_config(self):
        """更新其他字段时 llm_config 应保持不变"""
        templates = self.service.get_all_templates()
        llm_cfg = {"provider": "anthropic", "model": "claude-opus-4-7"}
        agent = self.service.create_agent(templates[0]["id"], "Preserve-Test", llm_cfg)

        updated = self.service.update_agent(agent["id"], {"name": "New-Name"})

        assert updated["name"] == "New-Name"
        assert updated["llm_config"] == llm_cfg

    def test_get_agent_returns_llm_config(self):
        """get_agent 应返回 llm_config"""
        templates = self.service.get_all_templates()
        llm_cfg = {"provider": "azure", "model": "gpt-4o-mini"}
        agent = self.service.create_agent(templates[0]["id"], "Get-Test", llm_cfg)

        retrieved = self.service.get_agent(agent["id"])

        assert retrieved["llm_config"] == llm_cfg

    def test_list_agents_includes_llm_config(self):
        """list_agents 返回的列表应包含 llm_config"""
        templates = self.service.get_all_templates()
        llm_cfg = {"provider": "deepseek", "model": "deepseek-chat"}
        self.service.create_agent(templates[0]["id"], "List-Test", llm_cfg)

        agents = self.service.list_agents()
        assert len(agents) > 0

        found = [a for a in agents if a["name"] == "List-Test"]
        assert len(found) == 1
        assert found[0]["llm_config"] == llm_cfg

    @pytest.mark.asyncio
    async def test_agent_chat_passes_llm_config_to_llm_service(self):
        """agent_chat 应将 llm_config 构建为 Agent Pydantic 模型传给 LLMService"""
        templates = self.service.get_all_templates()
        llm_cfg = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "temperature": 0.5,
            "max_tokens": 2048,
        }
        agent = self.service.create_agent(templates[0]["id"], "Chat-Test", llm_cfg)
        session = self.service.create_session("Test Session")
        session_id = session.id

        with patch(
            "app.services.llm.llm_service.LLMService.chat",
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = LLMResponse(
                content="Mock response",
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                model="claude-sonnet-4-6",
                finish_reason="stop"
            )

            await self.service.agent_chat(agent["id"], session_id, "Hello")

            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args.kwargs
            passed_agent = call_kwargs.get("agent")

            assert passed_agent is not None
            assert passed_agent.id == agent["id"]
            assert passed_agent.config.llm_config.provider == "anthropic"
            assert passed_agent.config.llm_config.model == "claude-sonnet-4-6"
            assert passed_agent.config.llm_config.temperature == 0.5
            assert passed_agent.config.llm_config.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_agent_chat_no_llm_config_passes_none_agent(self):
        """无 llm_config 时 agent_chat 传 agent=None 给 LLMService"""
        templates = self.service.get_all_templates()
        agent = self.service.create_agent(templates[0]["id"], "NoConfig-Chat")
        session = self.service.create_session("Test Session")
        session_id = session.id

        with patch(
            "app.services.llm.llm_service.LLMService.chat",
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = LLMResponse(
                content="Mock response",
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                model="deepseek-chat",
                finish_reason="stop"
            )

            await self.service.agent_chat(agent["id"], session_id, "Hello")

            call_kwargs = mock_chat.call_args.kwargs
            assert call_kwargs.get("agent") is None


class TestLLMServiceAgentConfig:
    """LLMService 使用 agent.llm_config 覆盖默认值"""

    def setup_method(self):
        self.llm_service = LLMService()
        self.llm_service._cost_records = []

    @pytest.mark.asyncio
    async def test_chat_uses_agent_model_from_config(self):
        """agent 有 llm_config 时使用 agent 的 model"""
        agent = AgentModel(
            id="test-agent-1",
            config=AgentConfig(
                name="TestAgent",
                role="backend",
                llm_config=LLMConfig(
                    provider="mock",
                    model="custom-mock-model",
                    temperature=0.3,
                    max_tokens=1000,
                )
            )
        )

        with patch.object(
            self.llm_service, "_get_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="OK",
                usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
                model="custom-mock-model",
                finish_reason="stop"
            ))
            mock_get_provider.return_value = mock_provider

            response = await self.llm_service.chat(
                messages=[Message(role="user", content="Hi")],
                agent=agent,
                track_cost=False,
            )

            mock_provider.chat.assert_called_once()
            provider_call_kwargs = mock_provider.chat.call_args.kwargs
            assert provider_call_kwargs["model"] == "custom-mock-model"
            assert provider_call_kwargs["temperature"] == 0.3
            assert provider_call_kwargs["max_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_chat_falls_back_to_defaults_when_no_agent(self):
        """无 agent 时使用 .env 全局默认值"""
        with patch.object(
            self.llm_service, "_get_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="OK",
                usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
                model="deepseek-chat",
                finish_reason="stop"
            ))
            mock_get_provider.return_value = mock_provider

            response = await self.llm_service.chat(
                messages=[Message(role="user", content="Hi")],
                agent=None,
                track_cost=False,
            )

            provider_call_kwargs = mock_provider.chat.call_args.kwargs
            assert provider_call_kwargs["model"] == self.llm_service.settings.default_llm_model

    @pytest.mark.asyncio
    async def test_chat_agent_no_llm_config_uses_defaults(self):
        """agent 存在但 config.llm_config 为 None 时使用全局默认"""
        agent = AgentModel(
            id="test-agent-2",
            config=AgentConfig(
                name="NoLLMAgent",
                role="tester",
                llm_config=None,
            )
        )

        with patch.object(
            self.llm_service, "_get_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="OK",
                usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
                model="deepseek-chat",
                finish_reason="stop"
            ))
            mock_get_provider.return_value = mock_provider

            response = await self.llm_service.chat(
                messages=[Message(role="user", content="Hi")],
                agent=agent,
                track_cost=False,
            )

            provider_call_kwargs = mock_provider.chat.call_args.kwargs
            assert provider_call_kwargs["model"] == self.llm_service.settings.default_llm_model

    @pytest.mark.asyncio
    async def test_chat_explicit_params_override_agent_config(self):
        """显式传参 model/temperature 应覆盖 agent 的 llm_config"""
        agent = AgentModel(
            id="test-agent-3",
            config=AgentConfig(
                name="OverrideAgent",
                role="backend",
                llm_config=LLMConfig(
                    provider="mock",
                    model="agent-model",
                    temperature=0.9,
                )
            )
        )

        with patch.object(
            self.llm_service, "_get_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="OK",
                usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
                model="explicit-model",
                finish_reason="stop"
            ))
            mock_get_provider.return_value = mock_provider

            response = await self.llm_service.chat(
                messages=[Message(role="user", content="Hi")],
                agent=agent,
                model="explicit-model",
                temperature=0.1,
                track_cost=False,
            )

            provider_call_kwargs = mock_provider.chat.call_args.kwargs
            assert provider_call_kwargs["model"] == "explicit-model"
            assert provider_call_kwargs["temperature"] == 0.1

    @pytest.mark.asyncio
    async def test_cost_record_uses_agent_model_name(self):
        """成本记录中的 model 应来自 agent 的 llm_config"""
        agent = AgentModel(
            id="cost-test-agent",
            config=AgentConfig(
                name="CostAgent",
                role="backend",
                llm_config=LLMConfig(
                    provider="mock",
                    model="cost-track-model",
                    temperature=0.7,
                )
            )
        )

        with patch.object(
            self.llm_service, "_get_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="Cost test",
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                model="cost-track-model",
                finish_reason="stop"
            ))
            mock_get_provider.return_value = mock_provider

            await self.llm_service.chat(
                messages=[Message(role="user", content="Track this")],
                agent=agent,
                track_cost=True,
                task_id="task-123",
            )

            records = self.llm_service._cost_records
            assert len(records) == 1
            assert records[0]["model"] == "cost-track-model"
            assert records[0]["agent_id"] == "cost-test-agent"
            assert records[0]["task_id"] == "task-123"
            assert records[0]["provider"] == "mock"

    @pytest.mark.asyncio
    async def test_cost_record_without_agent_uses_default_provider(self):
        """无 agent 时成本记录使用全局默认 provider"""
        with patch.object(
            self.llm_service, "_get_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="Default cost",
                usage={"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
                model="deepseek-chat",
                finish_reason="stop"
            ))
            mock_get_provider.return_value = mock_provider

            await self.llm_service.chat(
                messages=[Message(role="user", content="No agent")],
                agent=None,
                track_cost=True,
            )

            records = self.llm_service._cost_records
            assert len(records) == 1
            assert records[0]["model"] == self.llm_service.settings.default_llm_model
            assert records[0]["provider"] == self.llm_service.settings.default_llm_provider

    @pytest.mark.asyncio
    async def test_cost_summary_includes_correct_model(self):
        """get_cost_summary 的 by_model 应包含正确的 model 名"""
        agent = AgentModel(
            id="summary-agent",
            config=AgentConfig(
                name="SummaryAgent",
                role="frontend",
                llm_config=LLMConfig(
                    provider="mock",
                    model="summary-model-v2",
                    temperature=0.5,
                )
            )
        )

        with patch.object(
            self.llm_service, "_get_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(return_value=LLMResponse(
                content="Summary test",
                usage={"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
                model="summary-model-v2",
                finish_reason="stop"
            ))
            mock_get_provider.return_value = mock_provider

            await self.llm_service.chat(
                messages=[Message(role="user", content="Cost summary")],
                agent=agent,
                track_cost=True,
            )

            summary = self.llm_service.get_cost_summary()
            assert "summary-model-v2" in summary["by_model"]
            assert summary["by_model"]["summary-model-v2"]["calls"] == 1
            assert summary["by_model"]["summary-model-v2"]["tokens"] == 300

    @pytest.mark.asyncio
    async def test_multiple_agents_different_models_cost_tracking(self):
        """多个 Agent 使用不同 model 时成本分别统计"""
        with patch.object(
            self.llm_service, "_get_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(side_effect=[
                LLMResponse(
                    content="A", usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                    model="model-a", finish_reason="stop"
                ),
                LLMResponse(
                    content="B", usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
                    model="model-b", finish_reason="stop"
                ),
            ])
            mock_get_provider.return_value = mock_provider

            agent_a = AgentModel(
                id="agent-a", config=AgentConfig(name="A", role="backend",
                    llm_config=LLMConfig(provider="mock", model="model-a"))
            )
            agent_b = AgentModel(
                id="agent-b", config=AgentConfig(name="B", role="frontend",
                    llm_config=LLMConfig(provider="mock", model="model-b"))
            )

            await self.llm_service.chat(
                messages=[Message(role="user", content="A")], agent=agent_a, track_cost=True)
            await self.llm_service.chat(
                messages=[Message(role="user", content="B")], agent=agent_b, track_cost=True)

            summary = self.llm_service.get_cost_summary()

            assert "model-a" in summary["by_model"]
            assert "model-b" in summary["by_model"]
            assert summary["by_model"]["model-a"]["calls"] == 1
            assert summary["by_model"]["model-b"]["calls"] == 1
            assert summary["by_model"]["model-a"]["tokens"] == 15
            assert summary["by_model"]["model-b"]["tokens"] == 30
            assert summary["call_count"] == 2


class TestLLMConfigModel:
    """Agent/LLMConfig Pydantic 模型测试"""

    def test_llm_config_defaults(self):
        """LLMConfig 默认值"""
        cfg = LLMConfig()
        assert cfg.provider == "deepseek"
        assert cfg.model == "deepseek-chat"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens is None

    def test_llm_config_custom_values(self):
        """LLMConfig 自定义值"""
        cfg = LLMConfig(
            provider="openai",
            model="gpt-4o",
            temperature=0.2,
            max_tokens=8000,
        )
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.2
        assert cfg.max_tokens == 8000

    def test_llm_config_temperature_bounds(self):
        """LLMConfig temperature 应在 [0, 2] 范围内"""
        cfg = LLMConfig(temperature=0.0)
        assert cfg.temperature == 0.0

        cfg = LLMConfig(temperature=2.0)
        assert cfg.temperature == 2.0

    def test_agent_config_with_llm_config(self):
        """AgentConfig 包含 llm_config"""
        llm = LLMConfig(provider="anthropic", model="claude-sonnet-4-6")
        config = AgentConfig(name="Test", role="architect", llm_config=llm)

        assert config.llm_config is not None
        assert config.llm_config.provider == "anthropic"
        assert config.llm_config.model == "claude-sonnet-4-6"

    def test_agent_config_without_llm_config(self):
        """AgentConfig 不包含 llm_config（使用全局默认）"""
        config = AgentConfig(name="Test", role="tester")

        assert config.llm_config is None

    def test_agent_model_with_llm_config(self):
        """Agent 模型完整构建"""
        agent = AgentModel(
            id="full-agent",
            config=AgentConfig(
                name="FullAgent",
                role="devops",
                llm_config=LLMConfig(
                    provider="azure",
                    model="gpt-4o-mini",
                    temperature=1.2,
                    max_tokens=6000,
                )
            )
        )

        assert agent.config.llm_config.provider == "azure"
        assert agent.config.llm_config.model == "gpt-4o-mini"
        assert agent.config.llm_config.temperature == 1.2
        assert agent.config.llm_config.max_tokens == 6000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
