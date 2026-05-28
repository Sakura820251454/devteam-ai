"""工具执行器单元测试。

测试 ToolExecutor 的参数解析、错误处理、消息格式。
"""

import json
import pytest

from app.services.agent.tool_executor import ToolExecutor
from app.services.agent.tools import ToolDef, ToolRegistry


class TestToolExecutorInit:
    """构造器测试。"""

    def test_default_max_iterations(self):
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        assert executor.max_iterations == 8

    def test_custom_max_iterations(self):
        registry = ToolRegistry()
        executor = ToolExecutor(registry, max_iterations=3)
        assert executor.max_iterations == 3

    def test_get_registry_returns_configured(self):
        registry = ToolRegistry()
        registry.register(ToolDef(name="t1", description="", parameters={}, fn=lambda **k: "ok"))
        executor = ToolExecutor(registry)
        result = executor._get_registry()
        assert result is registry
        assert result.get("t1") is not None

    def test_get_registry_falls_back_to_global(self):
        """未配置 registry 时回退到全局注册中心。"""
        executor = ToolExecutor(None)
        reg = executor._get_registry()
        # 全局注册中心至少有 5 个工具
        tools = reg.get_openai_tools()
        assert len(tools) >= 5


class TestExecuteToolCall:
    """_execute_tool_call 参数解析测试。"""

    @pytest.fixture
    def executor(self):
        registry = ToolRegistry()

        async def echo_fn(project_id, **kwargs):
            return json.dumps({"project": project_id, "args": kwargs}, ensure_ascii=False)

        registry.register(ToolDef(
            name="echo",
            description="回显参数",
            parameters={"type": "object", "properties": {}},
            fn=echo_fn,
        ))
        return ToolExecutor(registry)

    @pytest.mark.asyncio
    async def test_execute_with_valid_json_args(self, executor):
        result = await executor._execute_tool_call(
            {
                "id": "call-1",
                "function": {
                    "name": "echo",
                    "arguments": '{"key": "value"}',
                },
            },
            project_id="proj-1",
        )
        assert "proj-1" in result
        parsed = json.loads(result)
        assert parsed["args"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_execute_with_dict_args(self, executor):
        """arguments 已经是 dict 而非 JSON 字符串时也能处理。"""
        result = await executor._execute_tool_call(
            {
                "id": "call-2",
                "function": {
                    "name": "echo",
                    "arguments": {"key": "dict_value"},
                },
            },
            project_id="proj-2",
        )
        parsed = json.loads(result)
        assert parsed["args"]["key"] == "dict_value"

    @pytest.mark.asyncio
    async def test_execute_with_invalid_json_falls_back_to_empty(self, executor):
        """arguments 不是合法 JSON 时回退为 {}。"""
        result = await executor._execute_tool_call(
            {
                "id": "call-3",
                "function": {
                    "name": "echo",
                    "arguments": "not valid json {{{",
                },
            },
            project_id="proj-3",
        )
        parsed = json.loads(result)
        assert parsed["args"] == {}

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_error(self, executor):
        result = await executor._execute_tool_call(
            {
                "id": "call-4",
                "function": {
                    "name": "nonexistent_tool",
                    "arguments": "{}",
                },
            },
            project_id="proj-4",
        )
        assert "[Error]" in result or "Unknown" in result

    @pytest.mark.asyncio
    async def test_execute_with_empty_function(self, executor):
        """function 字段为空时的处理。"""
        result = await executor._execute_tool_call(
            {"id": "call-5", "function": {}},
            project_id="proj-5",
        )
        assert "Error" in result or "Unknown" in result

    @pytest.mark.asyncio
    async def test_execute_with_empty_arguments_str(self, executor):
        result = await executor._execute_tool_call(
            {
                "id": "call-6",
                "function": {
                    "name": "echo",
                    "arguments": "",
                },
            },
            project_id="proj-6",
        )
        parsed = json.loads(result)
        assert parsed["args"] == {}


class TestMessageHandling:
    """Message 工具结果格式化。"""

    def test_tool_result_message_format(self):
        """验证 Message.tool_result 可正常创建。"""
        from app.core.llm import Message

        msg = Message.tool_result(
            tool_call_id="call-123",
            name="read_file",
            content="file content here",
        )
        assert msg.role == "tool"
        assert msg.tool_call_id == "call-123"
        assert msg.name == "read_file"
        assert msg.content == "file content here"
